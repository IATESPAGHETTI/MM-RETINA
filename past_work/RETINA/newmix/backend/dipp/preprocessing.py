import cv2
import numpy as np

def resize_with_aspect_ratio(image, target_size=(512, 512), pad_color=(0, 0, 0)):
    target_w, target_h = target_size
    h, w = image.shape[:2]

    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    padded = np.full((target_h, target_w, 3), pad_color, dtype=np.uint8)
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    padded[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    return padded

def apply_circular_mask(image):
    h, w = image.shape[:2]
    size = max(h, w)

    square_canvas = np.full((size, size, 3), 255, dtype=np.uint8)
    x_offset = (size - w) // 2
    y_offset = (size - h) // 2
    square_canvas[y_offset:y_offset + h, x_offset:x_offset + w] = image

    mask = np.zeros((size, size), dtype=np.uint8)
    center = (size // 2, size // 2)
    radius = min(h, w) // 2
    cv2.circle(mask, center, radius, 255, -1)

    masked = cv2.bitwise_and(square_canvas, square_canvas, mask=mask)
    white_background = np.full_like(square_canvas, 255)
    final = np.where(mask[:, :, np.newaxis] == 255, masked, white_background)

    return final

def preprocess_image(img_path):
    image = cv2.imread(img_path)
    if image is None:
        raise FileNotFoundError(f"Image not found at {img_path}")

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    blurred = cv2.GaussianBlur(l_channel, (3, 3), 0)
    unsharp_l = cv2.addWeighted(l_channel, 1.5, blurred, -0.5, 0)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_l = clahe.apply(unsharp_l)

    gamma = 1.2
    gamma_corrected_l = np.uint8(np.power(clahe_l / 255.0, gamma) * 255)

    final_lab = cv2.merge([gamma_corrected_l, a_channel, b_channel])
    final_bgr = cv2.cvtColor(final_lab, cv2.COLOR_LAB2BGR)

    final_resized_bgr = resize_with_aspect_ratio(final_bgr, (512, 512))
    final_circular_masked = apply_circular_mask(final_resized_bgr)

    img_array = final_circular_masked / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    return img_array
