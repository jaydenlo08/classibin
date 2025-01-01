{ pkgs ? import <nixpkgs> {}, libedgetpu ? pkgs.callPackage /etc/nixos/laptop/libedgetpu/libedgetpu.nix {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    gobject-introspection
    stdenv.cc.cc.lib   # need libstdc++.so.6
    protobuf
    gst_all_1.gstreamer
    gst_all_1.gst-plugins-base
    gst_all_1.gst-plugins-good
    gst_all_1.gst-plugins-bad
    gst_all_1.gst-plugins-ugly
    gst_all_1.gst-libav
    gst_all_1.gst-vaapi
    gst_all_1.gst-plugins-rs
    python312Packages.pygobject3
    gtk3
    gtk4
    labelImg
    ninja
    libglvnd
    pkg-config
    cmake
    glib
    libedgetpu
    edgetpu-compiler
  ];

  shellHook = ''
    export LD_LIBRARY_PATH=${libedgetpu}/lib:${pkgs.glib}/lib:${pkgs.gobject-introspection}/lib:${pkgs.gtk3}/lib:${pkgs.gtk4}/lib:${pkgs.libGL}/lib/:${pkgs.stdenv.cc.cc.lib}/lib:$(nix eval nixpkgs#zlib.outPath --raw)/lib:$LD_LIBRARY_PATH;
    export QT_QPA_PLATFORM=xcb;
    source .venv/bin/activate;
  '';
}

