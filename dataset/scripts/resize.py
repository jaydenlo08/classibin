import os
import cv2

DIM1 = 224
DIM2 = 224

def crop_to_square(image):
    height, width = image.shape[:2]
    
    # Determine the center crop area
    min_dim = min(height, width)
    top = (height - min_dim) // 2
    left = (width - min_dim) // 2
    
    # Crop the center square from the image
    return image[top:top+min_dim, left:left+min_dim]

def resize(image, dim1, dim2):
    # First crop the image to a square
    cropped_image = crop_to_square(image)
    # Then resize to the desired dimensions
    return cv2.resize(cropped_image, (dim1, dim2))

def fileWalk(directory, destPath):
    try:
        os.makedirs(destPath)
    except OSError:
        if not os.path.isdir(destPath):
            raise

    for subdir, dirs, files in os.walk(directory):
        for file in files:
            if len(file) <= 4 or file[-4:] != '.jpg':
                continue

            srcFilePath = os.path.join(subdir, file)
            destFilePath = os.path.join(destPath, file)

            # Check if file already exists and is the correct size
            if os.path.exists(destFilePath):
                existing_image = cv2.imread(destFilePath)
                if existing_image is not None:
                    existing_height, existing_width = existing_image.shape[:2]
                    if existing_height == DIM1 and existing_width == DIM2:
                        print(f"Skipping {file}, already resized.")
                        continue

            pic = cv2.imread(srcFilePath)
            if pic is None:
                continue  # Skip files that couldn't be opened as images

            # Resize (cropping to square and then resizing)
            picResized = resize(pic, DIM1, DIM2)

            # Save the resized image
            cv2.imwrite(destFilePath, picResized)
            print(f"Resized and saved {file}.")

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__))) # CD to script dir
    prepath = os.path.join(os.getcwd(), '../images-original')
    glassDir = os.path.join(prepath, 'glass')
    paperDir = os.path.join(prepath, 'paper')
    cardboardDir = os.path.join(prepath, 'cardboard')
    plasticDir = os.path.join(prepath, 'plastic')
    metalDir = os.path.join(prepath, 'metal')
    trashDir = os.path.join(prepath, 'trash')

    destPath = os.path.join(os.getcwd(), '../images-resized')
    try:
        os.makedirs(destPath)
    except OSError:
        if not os.path.isdir(destPath):
            raise

    # GLASS
    fileWalk(glassDir, os.path.join(destPath, 'glass'))

    # PAPER
    fileWalk(paperDir, os.path.join(destPath, 'paper'))

    # CARDBOARD
    fileWalk(cardboardDir, os.path.join(destPath, 'cardboard'))

    # PLASTIC
    fileWalk(plasticDir, os.path.join(destPath, 'plastic'))

    # METAL
    fileWalk(metalDir, os.path.join(destPath, 'metal'))

    # TRASH
    fileWalk(trashDir, os.path.join(destPath, 'trash'))

if __name__ == '__main__':
    main()

