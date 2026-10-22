import streamlit as st
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import numpy as np
import os
import matplotlib.pyplot as plt
from model import UNet
from skimage.segmentation import find_boundaries
import tensorflow as tf
import cv2
from scipy.stats import linregress

# --------------------------
# Preprocessing for HbA1c Models (from preprocessing.py)
# --------------------------
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

def preprocess_image_hba1c(image: Image.Image):
    """
    Preprocesses the image for the HbA1c models.
    This is an adaptation of the original function to work with a PIL image object.
    """
    image_cv = np.array(image)
    image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGB2BGR)
    
    lab = cv2.cvtColor(image_cv, cv2.COLOR_BGR2LAB)
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

# --------------------------
# Load Models
# --------------------------
@st.cache_resource
def load_unet_model():
    """Loads the UNet model from the saved weights."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = UNet().to(device)
    model.load_state_dict(torch.load("saved_model/unet_drive.pth", map_location=device))
    model.eval()
    return model, device

@st.cache_resource
def load_hba1c_models():
    """Loads the TensorFlow/Keras models for HbA1c classification."""
    try:
        binary_model = tf.keras.models.load_model("models/binary_final_best_hba1c_model.keras")
        multi_model = tf.keras.models.load_model("models/multi_final_best_hba1c_model.keras")
        return binary_model, multi_model
    except Exception as e:
        st.error(f"Could not load HbA1c models. Make sure the 'models' folder is correct.\nError: {e}")
        return None, None
    
@st.cache_resource
def load_av_model():
    try:
        model = torch.load("models/av_model.pth", map_location="cpu")
        model.eval()
        return model
    except Exception as e:
        st.warning(f"AV model not found: {e}")
        return None

av_model = load_av_model()

unet_model, unet_device = load_unet_model()
binary_hba1c_model, multi_hba1c_model = load_hba1c_models()

# --------------------------
# Prediction Function (for UNet)
# --------------------------
def predict_unet(image: Image.Image):
    """Generates a segmentation mask for the input retina image."""
    transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor()
    ])
    unet_model.eval()
    with torch.no_grad():
        img_tensor = transform(image).unsqueeze(0).to(unet_device)
        pred = unet_model(img_tensor)
        pred_mask = (pred.squeeze().cpu().numpy() > 0.5).astype(np.uint8) * 255
    return pred_mask
def av_classification(image):
    transform = transforms.Compose([
        transforms.Resize((512, 512)),
        transforms.ToTensor(),
    ])
    img_tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        preds = av_model(img_tensor)
    
    artery_mask = preds[0, 0].cpu().numpy()
    vein_mask = preds[0, 1].cpu().numpy()

    artery_mask = (artery_mask > 0.5).astype(np.uint8) * 255
    vein_mask = (vein_mask > 0.5).astype(np.uint8) * 255

    return Image.fromarray(artery_mask), Image.fromarray(vein_mask)

# --------------------------
# Fractal Dimension Calculations & Plotting
# --------------------------
def box_counting_plot(image_mask):
    binary_mask = (image_mask > 0).astype(np.uint8)
    boundaries = find_boundaries(binary_mask, mode='inner').astype(np.uint8)
    if not np.any(boundaries):
        st.warning("No boundaries found for fractal analysis.")
        return None, None
    box_sizes = np.logspace(0, np.log10(min(boundaries.shape) / 2), num=15, endpoint=False)
    counts = []
    for size in box_sizes:
        count = 0
        grid_rows = int(np.ceil(boundaries.shape[0] / size))
        grid_cols = int(np.ceil(boundaries.shape[1] / size))
        for r in range(grid_rows):
            for c in range(grid_cols):
                box = boundaries[int(r*size):int((r+1)*size), int(c*size):int((c+1)*size)]
                if np.any(box):
                    count += 1
        counts.append(count)
    log_sizes = -np.log(box_sizes)
    log_counts = np.log(counts)
    A = np.vstack([log_sizes, np.ones(len(log_sizes))]).T
    try:
        fractal_dimension, res, rank, s = np.linalg.lstsq(A, log_counts, rcond=None)
        intercept = fractal_dimension[1]
        fractal_dimension = fractal_dimension[0]
    except np.linalg.LinAlgError:
        st.error("Linear algebra error during fractal dimension calculation.")
        fractal_dimension = 0
        intercept = 0
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(log_sizes, log_counts, 'o', label='Data points')
    ax.plot(log_sizes, fractal_dimension * log_sizes + intercept, 'r', label=f'Fit (D = {fractal_dimension:.4f})')
    ax.set_title("Box-Counting Plot")
    ax.set_xlabel("log(1/Box Size)")
    ax.set_ylabel("log(Number of Boxes)")
    ax.legend()
    plt.tight_layout()
    return fig, fractal_dimension

def fourier_power_spectrum(image_mask):
    f = np.fft.fft2(image_mask)
    fshift = np.fft.fftshift(f)
    power_spectrum = np.abs(fshift)**2
    h, w = power_spectrum.shape
    center_y, center_x = h // 2, w // 2
    y, x = np.ogrid[:h, :w]
    r = np.sqrt((x - center_x)**2 + (y - center_y)**2)
    r_flat = r.ravel()
    power_flat = power_spectrum.ravel()
    radii = np.arange(int(r.max()))
    power_profile = np.zeros(len(radii))
    count_profile = np.zeros(len(radii))
    for i in range(len(r_flat)):
        if r_flat[i] < len(radii):
            power_profile[int(r_flat[i])] += power_flat[i]
            count_profile[int(r_flat[i])] += 1
    power_profile = np.divide(power_profile, count_profile, where=count_profile!=0)
    log_radii = np.log(radii[1:])
    log_power = np.log(power_profile[1:])
    valid_indices = np.isfinite(log_radii) & np.isfinite(log_power)
    log_radii_fit = log_radii[valid_indices]
    log_power_fit = log_power[valid_indices]
    if len(log_radii_fit) > 1:
        A_fourier = np.vstack([log_radii_fit, np.ones(len(log_radii_fit))]).T
        slope, intercept = np.linalg.lstsq(A_fourier, log_power_fit, rcond=None)[0]
    else:
        slope, intercept = 0, 0
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.loglog(radii[1:], power_profile[1:], 'o', label='Data points')
    ax.loglog(radii[1:], np.exp(intercept) * radii[1:]**slope, 'r', label=f'Fit (Slope = {slope:.4f})')
    ax.set_title("Fourier Power Spectrum (Radial Profile)")
    ax.set_xlabel("Spatial Frequency (k)")
    ax.set_ylabel("Power P(k)")
    ax.legend()
    plt.tight_layout()
    return fig

def multifractal_spectrum(image_mask):
    box_sizes = np.logspace(0, np.log10(min(image_mask.shape) / 2), num=10, endpoint=False)
    q_values = np.linspace(-5, 5, 21)
    Dq = []
    probabilities = []
    for size in box_sizes:
        box_probs = []
        grid_rows = int(np.ceil(image_mask.shape[0] / size))
        grid_cols = int(np.ceil(image_mask.shape[1] / size))
        total_mass = np.sum(image_mask > 0)
        if total_mass == 0:
            Dq = [0.0] * len(q_values)
            break
        for r in range(grid_rows):
            for c in range(grid_cols):
                box = image_mask[int(r*size):int((r+1)*size), int(c*size):int((c+1)*size)]
                mass_in_box = np.sum(box > 0)
                if mass_in_box > 0:
                    box_probs.append(mass_in_box / total_mass)
        probabilities.append(np.array(box_probs))
    for q in q_values:
        log_sums = []
        log_sizes = []
        for i in range(len(box_sizes)):
            size = box_sizes[i]
            probs = probabilities[i]
            if len(probs) > 0:
                if np.isclose(q, 1):
                    sum_val = -np.sum(probs * np.log(probs))
                else:
                    if q < 0:
                        probs_power_q = np.power(probs, q)
                        probs_power_q = np.nan_to_num(probs_power_q, nan=0.0, posinf=0.0)
                    else:
                        probs_power_q = np.power(probs, q)
                    sum_val = np.sum(probs_power_q)
                if sum_val > 0:
                    log_sums.append(np.log(sum_val))
                    log_sizes.append(np.log(size))
        if len(log_sizes) > 1:
            try:
                A = np.vstack([log_sizes, np.ones(len(log_sizes))]).T
                coeffs, _, _, _ = np.linalg.lstsq(A, log_sums, rcond=None)
                tau = coeffs[0]
                if not np.isclose(q, 1):
                    Dq.append(tau / (q - 1))
                else:
                    Dq.append(tau)
            except np.linalg.LinAlgError:
                Dq.append(0.0)
        else:
            Dq.append(0.0)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(q_values, Dq, 'o-')
    ax.set_title("Multifractal Spectrum (Dq vs q)")
    ax.set_xlabel("Moment Order, q")
    ax.set_ylabel("Generalized Dimension, Dq")
    plt.tight_layout()
    return fig

# --------------------------
# Streamlit UI
# --------------------------
st.title("🩺 Retina Image Analysis Toolkit")
st.write("Upload a retina image to get started.")

# Initialize session state for the mask if it doesn't exist
if 'image' not in st.session_state:
    st.session_state.image = None
if 'mask' not in st.session_state:
    st.session_state.mask = None

uploaded_file = st.file_uploader("Choose a retina image", type=["jpg", "png", "jpeg", "tif"])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")
    st.session_state.image = image
    st.image(image, caption="Uploaded Retina Image", use_column_width=True)

    st.subheader("Select an analysis to perform:")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("1. Calculate HbA1c", use_container_width=True):
            st.session_state.action = 'hba1c'
    with col2:
        if st.button("2. Show Segmentation", use_container_width=True):
            st.session_state.action = 'segmentation'
    with col3:
        if st.button("3. Show Fractal Analysis", use_container_width=True, disabled=(st.session_state.mask is None)):
            st.session_state.action = 'fractal'

    with col4:
        if st.button("Show A-V Classification", disabled=(av_model is None)):
            if av_model is None:
                st.error("AV model not available. Please ensure models/av_model.pth exists.")
            else:
                artery_img, vein_img = av_classification(image)
                st.subheader("Artery vs Vein Classification")
                st.image([artery_img, vein_img], caption=["Arteries", "Veins"], use_container_width=True)
    
    if 'action' in st.session_state and st.session_state.action:
        st.markdown("---")
        
        # --- Handle HbA1c Analysis ---
        if st.session_state.action == 'hba1c':
            if binary_hba1c_model is None or multi_hba1c_model is None:
                st.stop()
            st.subheader("HbA1c Classification Results")
            with st.spinner("Calculating HbA1c..."):
                try:
                    img_array = preprocess_image_hba1c(st.session_state.image)
                    
                    # Binary Classification
                    binary_prediction = binary_hba1c_model.predict(img_array)
                    is_positive = int(binary_prediction[0][0] > 0.5)
                    binary_confidence = binary_prediction[0][0] if is_positive else 1 - binary_prediction[0][0]
                    binary_label = "Positive" if is_positive else "Negative"
                    binary_hba1c_range = "≥6.5 (High Risk)" if is_positive else "3.7–5.6 (Normal)"
                    
                    st.markdown("##### Binary Classification")
                    st.markdown(f"**Prediction:** {binary_label}")
                    st.markdown(f"**Confidence:** {binary_confidence:.2%}")
                    st.markdown(f"**Estimated HbA1c Range:** {binary_hba1c_range}")

                    st.markdown("---")

                    # Multi-class Classification
                    multi_prediction = multi_hba1c_model.predict(img_array)
                    class_index = int(np.argmax(multi_prediction))
                    multi_confidence = multi_prediction[0][class_index]
                    hba1c_ranges = {0: "3.7–5.1", 1: "5.2–5.6", 2: "5.7–6.4", 3: "6.5–7.5", 4: "7.6–9.0", 5: ">9.0"}
                    multi_hba1c_range = hba1c_ranges.get(class_index, "Unknown")
                    
                    st.markdown("##### Multi-class Classification")
                    st.markdown(f"**Predicted Class:** {class_index}")
                    st.markdown(f"**Confidence:** {multi_confidence:.2%}")
                    st.markdown(f"**Estimated HbA1c Range:** {multi_hba1c_range}")

                except Exception as e:
                    st.error(f"Failed to perform HbA1c analysis: {e}")

        # --- Handle Segmentation and Fractal Analysis ---
        elif st.session_state.action == 'segmentation':
            st.subheader("Retinal Vessel Segmentation")
            with st.spinner('Segmenting the image...'):
                mask = predict_unet(st.session_state.image)
                st.session_state.mask = mask
            st.image(mask, caption="Predicted Vessel Mask", use_column_width=True, clamp=True)
            if np.any(mask):
                _, fractal_dim = box_counting_plot(mask)
                st.subheader("Box-Counting Fractal Dimension")
                st.metric(label="D", value=f"{fractal_dim:.4f}")
            else:
                st.error("No vessels detected for analysis.")
                st.session_state.mask = None
        
        elif st.session_state.action == 'fractal':
            st.subheader("Fractal Analysis Plots")
            if st.session_state.mask is None:
                st.warning("Please run segmentation first to generate the vessel mask.")
            else:
                with st.spinner('Generating plots...'):
                    # Box-Counting Plot
                    box_counting_fig, _ = box_counting_plot(st.session_state.mask)
                    if box_counting_fig:
                        st.pyplot(box_counting_fig)
                        st.markdown("---")

                    # Fourier Power Spectrum Plot
                    fourier_fig = fourier_power_spectrum(st.session_state.mask)
                    st.pyplot(fourier_fig)
                    st.markdown("---")
                    
                    # Multifractal Spectrum Plot
                    multifractal_fig = multifractal_spectrum(st.session_state.mask)
                    st.pyplot(multifractal_fig)
