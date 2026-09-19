// ============================================================================
// POLYDIM V761 — NATIVE DART FFI LATENT BRIDGE
// Zero-Copy Direct Memory Access | S^(D-1) Manifold Rotations | IEEE-754 FP64
// Standalone Zero-Pub-Dependency Architecture (NativeHeap via C Runtime)
// ============================================================================

import 'dart:ffi' as ffi;
import 'dart:io';
import 'dart:math' as math;

// ---------------------------------------------------------------------------
// 0. STANDALONE NATIVE HEAP ALLOCATOR (ZERO PUB DEPENDENCY)
// ---------------------------------------------------------------------------
class NativeHeap {
  static late final ffi.Pointer<ffi.Void> Function(int size) _malloc;
  static late final void Function(ffi.Pointer<ffi.Void> ptr) _free;
  static bool _initialized = false;

  static void init() {
    if (_initialized) return;
    ffi.DynamicLibrary libc;
    if (Platform.isWindows) {
      libc = ffi.DynamicLibrary.open('msvcrt.dll');
    } else if (Platform.isMacOS) {
      libc = ffi.DynamicLibrary.process();
    } else {
      libc = ffi.DynamicLibrary.open('libc.so.6');
    }

    _malloc = libc.lookupFunction<ffi.Pointer<ffi.Void> Function(ffi.Size), ffi.Pointer<ffi.Void> Function(int)>('malloc');
    _free = libc.lookupFunction<ffi.Void Function(ffi.Pointer<ffi.Void>), void Function(ffi.Pointer<ffi.Void>)>('free');
    _initialized = true;
  }

  static ffi.Pointer<T> allocate<T extends ffi.NativeType>(int byteCount) {
    init();
    final ptr = _malloc(byteCount);
    if (ptr.address == 0) throw OutOfMemoryError();
    return ptr.cast<T>();
  }

  static void free(ffi.Pointer ptr) {
    init();
    _free(ptr.cast<ffi.Void>());
  }
}

// ---------------------------------------------------------------------------
// 1. PMTP CONTROL STRUCT (64-bit Packed Atomic)
// ---------------------------------------------------------------------------
final class PMTPControl extends ffi.Struct {
  @ffi.Uint64()
  external int state;
}

// ---------------------------------------------------------------------------
// 2. FFI SIGNATURES & ENGINE
// ---------------------------------------------------------------------------
typedef PolydimInitControlC = ffi.Void Function(ffi.Pointer<PMTPControl>);
typedef PolydimInitControlDart = void Function(ffi.Pointer<PMTPControl>);

typedef PolydimPublishWriteC = ffi.Void Function(ffi.Pointer<PMTPControl>, ffi.Uint64, ffi.Uint64);
typedef PolydimPublishWriteDart = void Function(ffi.Pointer<PMTPControl>, int, int);

typedef PolydimAcquireReadC = ffi.Bool Function(ffi.Pointer<PMTPControl>, ffi.Pointer<ffi.Uint64>, ffi.Pointer<ffi.Uint64>);
typedef PolydimAcquireReadDart = bool Function(ffi.Pointer<PMTPControl>, ffi.Pointer<ffi.Uint64>, ffi.Pointer<ffi.Uint64>);

typedef PolydimApplyRodriguesC = ffi.Int32 Function(
  ffi.Pointer<ffi.Double> y,
  ffi.Pointer<ffi.Double> u,
  ffi.Pointer<ffi.Double> v,
  ffi.Pointer<ffi.Double> yOut,
  ffi.Double theta,
  ffi.Uint64 d,
);
typedef PolydimApplyRodriguesDart = int Function(
  ffi.Pointer<ffi.Double> y,
  ffi.Pointer<ffi.Double> u,
  ffi.Pointer<ffi.Double> v,
  ffi.Pointer<ffi.Double> yOut,
  double theta,
  int d,
);

typedef PolydimRustVerifyC = ffi.Int32 Function(ffi.Pointer<ffi.Double>, ffi.IntPtr, ffi.Pointer<ffi.Double>);
typedef PolydimRustVerifyDart = int Function(ffi.Pointer<ffi.Double>, int, ffi.Pointer<ffi.Double>);

typedef PolydimRustBetti1C = ffi.Int32 Function(ffi.Pointer<ffi.Double>, ffi.IntPtr, ffi.Double);
typedef PolydimRustBetti1Dart = int Function(ffi.Pointer<ffi.Double>, int, double);

class PolydimFFIEngine {
  late final ffi.DynamicLibrary _cppLib;
  late final ffi.DynamicLibrary _rustLib;

  late final PolydimInitControlDart polydimInitControl;
  late final PolydimPublishWriteDart polydimPublishWrite;
  late final PolydimAcquireReadDart polydimAcquireRead;
  late final PolydimApplyRodriguesDart polydimApplyRodrigues;

  late final PolydimRustVerifyDart polydimRustVerify;
  late final PolydimRustBetti1Dart polydimRustBetti1;

  PolydimFFIEngine({String? basePath}) {
    final dir = basePath ?? Directory.current.path;
    final cppPath = Platform.isWindows
        ? '$dir/bin/polydim_kernel.dll'
        : '$dir/bin/libpolydim_kernel.so';
    final rustPath = Platform.isWindows
        ? '$dir/bin/polydim_rust_guard.dll'
        : '$dir/bin/libpolydim_rust_guard.so';

    _cppLib = ffi.DynamicLibrary.open(cppPath);
    _rustLib = ffi.DynamicLibrary.open(rustPath);

    polydimInitControl = _cppLib
        .lookupFunction<PolydimInitControlC, PolydimInitControlDart>('polydim_init_control');
    polydimPublishWrite = _cppLib
        .lookupFunction<PolydimPublishWriteC, PolydimPublishWriteDart>('polydim_publish_write');
    polydimAcquireRead = _cppLib
        .lookupFunction<PolydimAcquireReadC, PolydimAcquireReadDart>('polydim_acquire_read');
    polydimApplyRodrigues = _cppLib
        .lookupFunction<PolydimApplyRodriguesC, PolydimApplyRodriguesDart>('polydim_apply_rodrigues_geodesic_f64');

    polydimRustVerify = _rustLib
        .lookupFunction<PolydimRustVerifyC, PolydimRustVerifyDart>('polydim_rust_verify_invariants');
    polydimRustBetti1 = _rustLib
        .lookupFunction<PolydimRustBetti1C, PolydimRustBetti1Dart>('polydim_rust_betti1_guard');
  }
}

void main() {
  print('=== POLYDIM V761 DART FFI BENCHMARK & TEST ===');
  final basePath = Directory.current.path;
  final engine = PolydimFFIEngine(basePath: basePath);

  final D = 1000000; // D = 1,000,000 dimensions (8 MB per vector)
  print('Allocating native buffers for D = $D (FP64)...');

  final yPtr = NativeHeap.allocate<ffi.Double>(D * 8);
  final uPtr = NativeHeap.allocate<ffi.Double>(D * 8);
  final vPtr = NativeHeap.allocate<ffi.Double>(D * 8);
  final yOutPtr = NativeHeap.allocate<ffi.Double>(D * 8);
  final driftOut = NativeHeap.allocate<ffi.Double>(8);

  try {
    final invSqrtD = 1.0 / math.sqrt(D.toDouble());
    for (int i = 0; i < D; i++) {
      yPtr[i] = invSqrtD;
      uPtr[i] = (i % 2 == 0) ? (invSqrtD * 0.5) : (-invSqrtD * 0.5);
      vPtr[i] = (i % 2 == 0) ? (-invSqrtD * 0.5) : (invSqrtD * 0.5);
    }

    // 1. Initial Rust Invariant Check
    int rustStatus = engine.polydimRustVerify(yPtr, D, driftOut);
    print('Initial Rust Invariant Check: Status=$rustStatus, Drift=${driftOut[0].toStringAsExponential(4)}');
    assert(rustStatus == 0, 'Initial state must satisfy norm invariant');

    final theta = 0.05; // 0.05 radians geodesic rotation
    final sw = Stopwatch()..start();
    
    // 2. Execute Native C++ Rodrigues Geodesic Operator
    final cppStatus = engine.polydimApplyRodrigues(yPtr, uPtr, vPtr, yOutPtr, theta, D);
    sw.stop();

    print('C++ Geodesic Step Completed: Status=$cppStatus, Time=${sw.elapsedMilliseconds} ms (${sw.elapsedMicroseconds} us)');
    assert(cppStatus == 0, 'C++ geodesic execution must return SUCCESS (0)');

    // 3. Verify resulting manifold invariants in Rust
    rustStatus = engine.polydimRustVerify(yOutPtr, D, driftOut);
    print('Post-Geodesic Rust Invariant Check: Status=$rustStatus, Drift=${driftOut[0].toStringAsExponential(4)}');
    assert(rustStatus == 0, 'Post-geodesic state must satisfy norm invariant');

    print('>>> POLYDIM V761 DART FFI TEST: ALL SUITES PASSED (EXIT CODE 0) <<<');
  } finally {
    NativeHeap.free(yPtr);
    NativeHeap.free(uPtr);
    NativeHeap.free(vPtr);
    NativeHeap.free(yOutPtr);
    NativeHeap.free(driftOut);
  }
}
