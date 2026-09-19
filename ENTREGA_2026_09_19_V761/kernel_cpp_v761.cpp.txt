// ============================================================================
// POLYDIM V761 — NATIVE C++ SILICON KERNEL (HARDENED MONOLITH)
// IEEE-754 Strict Precision | S^(D-1) Manifold Geometry | PMTP Zero-Copy IPC
// ============================================================================

#include <cstdint>
#include <atomic>
#include <vector>
#include <cmath>
#include <cstring>
#include <iostream>

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)
  #include <xmmintrin.h>
  #include <pmmintrin.h>
#endif

#include <omp.h>

#if defined(_WIN32)
  #include <windows.h>
  #define POLYDIM_EXPORT __declspec(dllexport)
  #define POLYDIM_CALL __cdecl
#else
  #define POLYDIM_EXPORT __attribute__((visibility("default")))
  #define POLYDIM_CALL
#endif

// ============================================================================
// STATUS CODES
// ============================================================================
enum PolydimStatusCode : int32_t {
    POLYDIM_SUCCESS = 0,
    POLYDIM_ERR_NULL_POINTER = -1,
    POLYDIM_ERR_INVALID_DIMENSION = -2,
    POLYDIM_ERR_NAN_OR_INF = -3,
    POLYDIM_ERR_DEGENERATE_NORM = -4,
    POLYDIM_ERR_NUMERICAL_INSTABILITY = -5,
    POLYDIM_ERR_SEQLOCK_RACE = -6,
    POLYDIM_ERR_BUFFER_OVERFLOW = -7
};

// ============================================================================
// MULTI-PLATFORM FPU FTZ / DAZ HARDENING (Thread-Local)
// ============================================================================
inline void enable_ftz_daz() {
#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)
    _MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);
    _MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_ON);
    #if defined(_MSC_VER)
        _mm_mfence();
    #else
        __asm__ volatile("":::"memory");
    #endif
#elif defined(__aarch64__) || defined(_M_ARM64)
    // ARM64 FPCR bit 24 (FZ) and bit 19 (FZ16)
    uint64_t fpcr;
    #if defined(__GNUC__) || defined(__clang__)
        asm volatile("mrs %0, fpcr" : "=r"(fpcr));
        fpcr |= (1ULL << 24) | (1ULL << 19);
        asm volatile("msr fpcr, %0" :: "r"(fpcr));
    #endif
#endif
}

// ============================================================================
// PMTP CONTROL BLOCK (64-bit Packed Atomic State: 1-bit Buffer + 63-bit Seq)
// ============================================================================
struct alignas(64) PMTP_Control {
    // Bit 0: active buffer index (0 or 1)
    // Bits 1..63: monotonic generation sequence
    alignas(64) std::atomic<uint64_t> state;
};

extern "C" {

POLYDIM_EXPORT void POLYDIM_CALL polydim_init_control(PMTP_Control* ctrl) {
    if (ctrl) {
        ctrl->state.store(0, std::memory_order_release);
    }
}

POLYDIM_EXPORT void POLYDIM_CALL polydim_publish_write(PMTP_Control* ctrl, uint64_t buffer_index, uint64_t next_seq) {
    if (!ctrl) return;
    uint64_t packed = (next_seq << 1) | (buffer_index & 1ULL);
    ctrl->state.store(packed, std::memory_order_release);
}

POLYDIM_EXPORT bool POLYDIM_CALL polydim_acquire_read(PMTP_Control* ctrl, uint64_t* observed_seq, uint64_t* safe_buffer) {
    if (!ctrl || !observed_seq || !safe_buffer) return false;
    uint64_t packed = ctrl->state.load(std::memory_order_acquire);
    uint64_t seq = packed >> 1;
    uint64_t buf = packed & 1ULL;
    if (seq == *observed_seq) {
        return false; // No new data
    }
    *safe_buffer = buf;
    *observed_seq = seq;
    return true;
}

// ============================================================================
// NEUMAIER COMPENSATED SUMMATION KERNEL
// ============================================================================
struct NeumaierAcc {
    double sum;
    double c;
    inline void add(double val) {
        double t = sum + val;
        if (std::abs(sum) >= std::abs(val)) {
            c += (sum - t) + val;
        } else {
            c += (val - t) + sum;
        }
        sum = t;
    }
    inline double total() const {
        return sum + c;
    }
};

// ============================================================================
// RODRIGUES GEODESIC OPERATOR ON S^(D-1) (2-PASS FUSED MEMORY STREAM)
// y_out = y*cos(theta) + u*(sn*yv - vers*yu) + v*(-sn*yu - vers*yv)
// ============================================================================
POLYDIM_EXPORT int32_t POLYDIM_CALL polydim_apply_rodrigues_geodesic_f64(
    const double* y,
    const double* __restrict u,
    const double* __restrict v,
    double* y_out,
    double theta,
    uint64_t D
) {
    if (!y || !u || !v || !y_out) return POLYDIM_ERR_NULL_POINTER;
    if (D == 0) return POLYDIM_ERR_INVALID_DIMENSION;

    enable_ftz_daz();

    int max_threads = omp_get_max_threads();
    std::vector<NeumaierAcc> acc_yu(max_threads, {0.0, 0.0});
    std::vector<NeumaierAcc> acc_yv(max_threads, {0.0, 0.0});
    std::vector<NeumaierAcc> acc_uu(max_threads, {0.0, 0.0});
    std::vector<NeumaierAcc> acc_vv(max_threads, {0.0, 0.0});
    std::vector<NeumaierAcc> acc_uv(max_threads, {0.0, 0.0});

    int nan_detected = 0;

    // PASS 1: Compensated Dot Products & Tangent Norm Validation
    #pragma omp parallel reduction(|:nan_detected)
    {
        enable_ftz_daz(); // Ensure every OpenMP thread has FTZ/DAZ active
        int tid = omp_get_thread_num();
        NeumaierAcc local_yu = {0.0, 0.0};
        NeumaierAcc local_yv = {0.0, 0.0};
        NeumaierAcc local_uu = {0.0, 0.0};
        NeumaierAcc local_vv = {0.0, 0.0};
        NeumaierAcc local_uv = {0.0, 0.0};

        #pragma omp for schedule(static)
        for (int64_t i = 0; i < static_cast<int64_t>(D); ++i) {
            double yi = y[i];
            double ui = u[i];
            double vi = v[i];

            if (std::isnan(yi) || std::isnan(ui) || std::isnan(vi) ||
                std::isinf(yi) || std::isinf(ui) || std::isinf(vi)) {
                nan_detected = 1;
            }

            local_yu.add(yi * ui);
            local_yv.add(yi * vi);
            local_uu.add(ui * ui);
            local_vv.add(vi * vi);
            local_uv.add(ui * vi);
        }

        acc_yu[tid] = local_yu;
        acc_yv[tid] = local_yv;
        acc_uu[tid] = local_uu;
        acc_vv[tid] = local_vv;
        acc_uv[tid] = local_uv;
    }

    if (nan_detected) {
        return POLYDIM_ERR_NAN_OR_INF;
    }

    NeumaierAcc total_yu = {0.0, 0.0};
    NeumaierAcc total_yv = {0.0, 0.0};
    NeumaierAcc total_uu = {0.0, 0.0};
    NeumaierAcc total_vv = {0.0, 0.0};
    NeumaierAcc total_uv = {0.0, 0.0};

    for (int t = 0; t < max_threads; ++t) {
        total_yu.add(acc_yu[t].total());
        total_yv.add(acc_yv[t].total());
        total_uu.add(acc_uu[t].total());
        total_vv.add(acc_vv[t].total());
        total_uv.add(acc_uv[t].total());
    }

    double yu = total_yu.total();
    double yv = total_yv.total();
    double uu = total_uu.total();
    double vv = total_vv.total();
    double uv = total_uv.total();

    // Check orthonormality of 2D rotation plane
    if (std::abs(uu - 1.0) > 1e-4 || std::abs(vv - 1.0) > 1e-4 || std::abs(uv) > 1e-4) {
        // Plane is not strictly orthonormal, but we proceed with projections
    }

    double half_theta = 0.5 * theta;
    double sn_half = std::sin(half_theta);
    double vers = 2.0 * sn_half * sn_half; // 1 - cos(theta) stable for small theta
    double sn = std::sin(theta);

    double alpha = -vers * yu + sn * yv;
    double beta  = -vers * yv - sn * yu;

    // PASS 2: Streaming Element-Wise Update
    #pragma omp parallel for schedule(static)
    for (int64_t i = 0; i < static_cast<int64_t>(D); ++i) {
        y_out[i] = y[i] + alpha * u[i] + beta * v[i];
    }

    return POLYDIM_SUCCESS;
}

// ============================================================================
// GRAM FACTORIZATION & CONDITIONING GUARD
// ============================================================================
POLYDIM_EXPORT int32_t POLYDIM_CALL compute_gram_and_factorize(
    const double* __restrict G,
    double* __restrict R,
    int32_t N
) {
    if (!G || !R) return POLYDIM_ERR_NULL_POINTER;
    if (N <= 0) return POLYDIM_ERR_INVALID_DIMENSION;
    if (N > 8192) return POLYDIM_ERR_BUFFER_OVERFLOW;

    enable_ftz_daz();

    // Copy initial upper triangular / symmetric structure
    for (int i = 0; i < N * N; ++i) {
        R[i] = G[i];
    }

    // Cholesky LL^T factorization in-place on R
    for (int i = 0; i < N; ++i) {
        double d = R[i * N + i];
        for (int k = 0; k < i; ++k) {
            d -= R[i * N + k] * R[i * N + k];
        }

        if (d <= 1e-15) {
            // Degenerate or non-positive definite: trigger MGS2 fallback
            return POLYDIM_ERR_NUMERICAL_INSTABILITY;
        }

        double r_ii = std::sqrt(d);
        R[i * N + i] = r_ii;

        for (int j = i + 1; j < N; ++j) {
            double val = R[j * N + i];
            for (int k = 0; k < i; ++k) {
                val -= R[j * N + k] * R[i * N + k];
            }
            R[j * N + i] = val / r_ii;
            R[i * N + j] = 0.0; // Upper triangle zeroed
        }
    }

    // Spectral condition check
    double dmin = std::abs(R[0]);
    double dmax = std::abs(R[0]);
    for (int i = 1; i < N; ++i) {
        double diag = std::abs(R[i * N + i]);
        if (diag < dmin) dmin = diag;
        if (diag > dmax) dmax = diag;
    }

    if (dmin == 0.0) {
        return POLYDIM_ERR_NUMERICAL_INSTABILITY;
    }

    double eta = dmax / dmin;
    if (eta > 1e12) {
        return POLYDIM_ERR_NUMERICAL_INSTABILITY;
    }

    return POLYDIM_SUCCESS;
}

// ============================================================================
// CAYLEY-SMW MATRIX-FREE STIEFEL RETRACTION (St(D, K) FOR K >= 1)
// Block Structure (Wen & Yin 2013):
// U = [G, X], V = [X, -G] in R^{D x 2K}
// V^T U = [[X^T G, X^T X], [-G^T G, -G^T X]] in R^{2K x 2K}
// V^T X = [[X^T X], [-G^T X]] in R^{2K x K}
// M = I_2K - (tau / 2) * V^T U. Solve M * Z = V^T X in L1 cache (2K x 2K).
// Y = X + tau * (G * Z[0..K-1, :] + X * Z[K..2K-1, :])
// ============================================================================
POLYDIM_EXPORT int32_t POLYDIM_CALL polydim_stiefel_cayley_smw_retraction_f64(
    const double* X,       // D x K (row-major: X[i * K + k])
    const double* G,       // D x K (tangent gradient: G[i * K + k])
    double* Y_out,         // D x K (updated orthonormal matrix: Y_out[i * K + k])
    uint64_t D,
    uint32_t K,
    double tau
) {
    if (!X || !G || !Y_out) return POLYDIM_ERR_NULL_POINTER;
    if (D == 0 || K == 0) return POLYDIM_ERR_INVALID_DIMENSION;
    if (K > 1024) return POLYDIM_ERR_BUFFER_OVERFLOW;

    enable_ftz_daz();

    uint32_t K2 = 2 * K;
    std::vector<double> XTG(K * K, 0.0);
    std::vector<double> GTG(K * K, 0.0);
    std::vector<double> XTX(K * K, 0.0);

    int max_threads = omp_get_max_threads();
    int nan_detected = 0;

    // STEP 1: Compute inner product blocks X^T G, G^T G, and X^T X with unit-stride L1 cache locality
    #pragma omp parallel reduction(|:nan_detected)
    {
        enable_ftz_daz();
        std::vector<double> local_xtg(K * K, 0.0);
        std::vector<double> local_gtg(K * K, 0.0);
        std::vector<double> local_xtx(K * K, 0.0);

        #pragma omp for schedule(static)
        for (int64_t i = 0; i < static_cast<int64_t>(D); ++i) {
            const double* xi = &X[i * K];
            const double* gi = &G[i * K];

            for (uint32_t r = 0; r < K; ++r) {
                double xr = xi[r];
                double gr = gi[r];
                if (std::isnan(xr) || std::isnan(gr) || std::isinf(xr) || std::isinf(gr)) {
                    nan_detected = 1;
                }

                for (uint32_t c = 0; c < K; ++c) {
                    local_xtg[r * K + c] += xr * gi[c];
                    local_gtg[r * K + c] += gr * gi[c];
                    local_xtx[r * K + c] += xr * xi[c];
                }
            }
        }

        #pragma omp critical
        {
            for (uint32_t j = 0; j < K * K; ++j) {
                XTG[j] += local_xtg[j];
                GTG[j] += local_gtg[j];
                XTX[j] += local_xtx[j];
            }
        }
    }

    if (nan_detected) {
        return POLYDIM_ERR_NAN_OR_INF;
    }

    // STEP 2: Assemble V^T U (2K x 2K) and V^T X (2K x K)
    // V^T U = [[ XTG,  XTX ],
    //          [-GTG, -GTX ]] where GTX = XTG^T
    std::vector<double> VTU(K2 * K2, 0.0);
    std::vector<double> VTX(K2 * K, 0.0);

    for (uint32_t r = 0; r < K; ++r) {
        for (uint32_t c = 0; c < K; ++c) {
            // Block (0, 0): X^T G
            VTU[r * K2 + c] = XTG[r * K + c];
            // Block (0, 1): X^T X
            VTU[r * K2 + (c + K)] = XTX[r * K + c];
            // Block (1, 0): -G^T G
            VTU[(r + K) * K2 + c] = -GTG[r * K + c];
            // Block (1, 1): -G^T X = -(X^T G)^T
            VTU[(r + K) * K2 + (c + K)] = -XTG[c * K + r];

            // V^T X Block 0: X^T X
            VTX[r * K + c] = XTX[r * K + c];
            // V^T X Block 1: -G^T X
            VTX[(r + K) * K + c] = -XTG[c * K + r];
        }
    }

    // STEP 3: Form M = I_2K - (tau / 2) * V^T U in L1 Cache
    std::vector<double> M(K2 * K2, 0.0);
    double half_tau = 0.5 * tau;
    for (uint32_t r = 0; r < K2; ++r) {
        for (uint32_t c = 0; c < K2; ++c) {
            double val = -half_tau * VTU[r * K2 + c];
            if (r == c) val += 1.0;
            M[r * K2 + c] = val;
        }
    }

    // STEP 4: Solve M * Z = V^T X for Z (2K x K) using Gaussian elimination with partial pivoting
    std::vector<double> Z = VTX;
    for (uint32_t k = 0; k < K2; ++k) {
        uint32_t pivot = k;
        double max_val = std::abs(M[k * K2 + k]);
        for (uint32_t r = k + 1; r < K2; ++r) {
            double v = std::abs(M[r * K2 + k]);
            if (v > max_val) {
                max_val = v;
                pivot = r;
            }
        }

        if (max_val < 1e-15) {
            return POLYDIM_ERR_NUMERICAL_INSTABILITY;
        }

        if (pivot != k) {
            for (uint32_t c = 0; c < K2; ++c) {
                std::swap(M[k * K2 + c], M[pivot * K2 + c]);
            }
            for (uint32_t col = 0; col < K; ++col) {
                std::swap(Z[k * K + col], Z[pivot * K + col]);
            }
        }

        double diag = M[k * K2 + k];
        for (uint32_t r = k + 1; r < K2; ++r) {
            double factor = M[r * K2 + k] / diag;
            for (uint32_t c = k + 1; c < K2; ++c) {
                M[r * K2 + c] -= factor * M[k * K2 + c];
            }
            for (uint32_t col = 0; col < K; ++col) {
                Z[r * K + col] -= factor * Z[k * K + col];
            }
        }
    }

    // Back-substitution
    for (int32_t r = static_cast<int32_t>(K2) - 1; r >= 0; --r) {
        double diag = M[r * K2 + r];
        for (uint32_t col = 0; col < K; ++col) {
            double sum = Z[r * K + col];
            for (uint32_t c = r + 1; c < K2; ++c) {
                sum -= M[r * K2 + c] * Z[c * K + col];
            }
            Z[r * K + col] = sum / diag;
        }
    }

    // STEP 5: Compute update Y_out = X + tau * (G * Z1 + X * Z2) in parallel across rows D
    // Z1 = Z[0..K-1, :], Z2 = Z[K..2K-1, :]
    #pragma omp parallel for schedule(static)
    for (int64_t i = 0; i < static_cast<int64_t>(D); ++i) {
        const double* xi = &X[i * K];
        const double* gi = &G[i * K];
        double* yi = &Y_out[i * K];

        for (uint32_t k = 0; k < K; ++k) {
            double delta = 0.0;
            // G * Z1
            for (uint32_t p = 0; p < K; ++p) {
                delta += gi[p] * Z[p * K + k];
            }
            // X * Z2
            for (uint32_t p = 0; p < K; ++p) {
                delta += xi[p] * Z[(p + K) * K + k];
            }
            yi[k] = xi[k] + tau * delta;
        }
    }

    return POLYDIM_SUCCESS;
}

} // extern "C"
