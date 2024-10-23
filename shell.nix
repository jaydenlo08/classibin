{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    (python39.withPackages (ps: [ps.pip]))
    python39Packages.numpy
    python39Packages.gst-python
    python39Packages.pygobject3
    stdenv.cc.cc.lib   # need libstdc++.so.6
    protobuf
    gst_all_1.gstreamer
    gst_all_1.gst-plugins-base
    gst_all_1.gst-plugins-good
    gst_all_1.gst-plugins-bad
    gst_all_1.gst-plugins-ugly
    gst_all_1.gst-libav
    gst_all_1.gst-vaapi
    gtk3
    ];
    shellHook = ''
        export "LD_LIBRARY_PATH=/nix/store/zjmfnryzhs5rw2zsc0f0dppvg504d121-libedgetpu-grouper/lib:${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH"
        source .venv/bin/activate
    '';
}
