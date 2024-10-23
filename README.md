# ClassiBin

Your phil-recycling friend

## My `nix` environment
* `shell.nix` triggered by `direnv`
* Activates a python `venv` shell

## Requirements
* A NixOS system or other Unix-like system with dependences installed
* Python 3.12 with `venv`. Most of which could be installed via `pip install -r .requirements.txt`. Note that the `pycoral` & `tflite-runtime` packages has to be installed manually from wheels provided [here](https://github.com/virnik0/pycoral_builds). There are no official builds beyond Python 3.12.
* A [Google Coral USB Accelerator](https://coral.ai/products/accelerator) with EdgeTPU Runtime correctly installed.

## Dataset
* The [Trashnet](https://github.com/garythung/trashnet) dataset is used for this project. Credits to @garythung
* Due to file size limitation, the `images-original` directory needs to be downloaded from the [official site](https://huggingface.co/datasets/garythung/trashnet/tree/main) (direct link [here](https://huggingface.co/datasets/garythung/trashnet/blob/main/dataset-original.zip)) and placed in `dataset/images-original`

## Files

#### 📜 classify.py
* Classifies the recyclables from camera through GStreamer
* Refer to `python3 classify.py --help` for options
* The default options should work the best for most cases

#### 📜 dataset/scripts/resize.py
* Resizes images from `dataset/images-original` to `dataset/images-resized`
* The dimension could be adjusted through the `DIM1` & `DIM2` constants

#### 📜 dataset/scripts/retrain.py
* Trains the images from `dataset/images-resized` using MobileNet V2 by [transfer learning](https://coral.ai/docs/edgetpu/models-intro/#transfer-learning)
* The program automatically converts it to TensorFlow Lite and then compiles it for TPU.
