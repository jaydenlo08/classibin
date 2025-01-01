/* NIX shell for INFERENCING

COMMON:
pip install opencv-python pillow
pip uninstall numpy # PyCoral requires NumPy 1
pip install "numpy<2.0"

Pi:
pip install https://github.com/feranick/TFlite-builds/releases/download/v2.17.0/tflite_runtime-2.17.0-cp312-cp312-linux_aarch64.whl https://github.com/feranick/pycoral/releases/download/2.0.2TF2.17.0/pycoral-2.0.2-cp312-cp312-linux_aarch64.whl rpi-gpio

X86_64:
pip install https://github.com/feranick/TFlite-builds/releases/download/v2.17.0/tflite_runtime-2.17.0-cp312-cp312-linux_x86_64.whl https://github.com/feranick/pycoral/releases/download/2.0.2TF2.17.0/pycoral-2.0.2-cp312-cp312-linux_x86_64.whl

*/

{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  shellHook = ''
    export LD_LIBRARY_PATH=${pkgs.zlib.out}/lib:${pkgs.libedgetpu}/lib:${pkgs.glib.out}/lib:${pkgs.libGL}/lib/:${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH;
    source .venv/bin/activate;
  '';
}

