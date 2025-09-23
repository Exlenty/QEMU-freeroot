#!/bin/bash

# Check if required arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_tar.gz> <output_qcow2>"
    exit 1
fi

INPUT_TAR="$1"
OUTPUT_QCOW2="$2"
TEMP_DIR=$(mktemp -d)

# Check if input file exists
if [ ! -f "$INPUT_TAR" ]; then
    echo "Error: Input file '$INPUT_TAR' not found."
    exit 1
fi

# Decompress the tar.gz file
echo "Decompressing '$INPUT_TAR' to temporary directory '$TEMP_DIR'..."
tar -xzf "$INPUT_TAR" -C "$TEMP_DIR"
if [ $? -ne 0 ]; then
    echo "Error: Failed to decompress the tarball."
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Calculate required disk size (add a buffer)
REQUIRED_SIZE=$(du -sh --block-size=1G "$TEMP_DIR" | awk '{print $1}' | sed 's/G//')
if [ -z "$REQUIRED_SIZE" ]; then
    echo "Error: Could not determine the size of the temporary directory."
    rm -rf "$TEMP_DIR"
    exit 1
fi
DISK_SIZE=$((REQUIRED_SIZE + 2)) # Add 2GB buffer

echo "Creating a new qcow2 image of size ${DISK_SIZE}G..."
qemu-img create -f qcow2 "$OUTPUT_QCOW2" "${DISK_SIZE}G"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create the qcow2 image."
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Copy files into the qcow2 image
echo "Copying files from '$TEMP_DIR' to '$OUTPUT_QCOW2'..."

# Create a temporary mount point
MOUNT_POINT=$(mktemp -d)

# Mount the qcow2 image (requires libguestfs-tools, which provides guestmount)
if command -v guestmount &> /dev/null; then
    guestmount -a "$OUTPUT_QCOW2" -m /dev/sda1 "$MOUNT_POINT"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to mount the qcow2 image. Make sure it has a partition."
        # Fallback to direct copying, which is less reliable
        echo "Attempting to copy directly, this may not work for all images."
        rsync -av "$TEMP_DIR/" "$MOUNT_POINT/"
    else
        rsync -av "$TEMP_DIR/" "$MOUNT_POINT/"
        guestunmount "$MOUNT_POINT"
    fi
else
    echo "guestmount not found. This script is unable to copy files into the image."
    echo "You may need to manually mount and copy the files or use a different method."
    rm -rf "$TEMP_DIR" "$MOUNT_POINT"
    exit 1
fi

# Clean up
echo "Cleaning up temporary directories..."
rm -rf "$TEMP_DIR" "$MOUNT_POINT"

echo "Conversion complete! The qcow2 image is located at '$OUTPUT_QCOW2'."
