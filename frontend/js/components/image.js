// Phones take 8–12 MB photos. Shrinking them first makes uploads far faster on mobile data
// and the model only looks at a small version anyway.
const MAX_SIDE = 1600;

export async function prepareImage(file) {
  if (!file.type.startsWith("image/")) throw new Error("Please choose an image file (JPG or PNG).");
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = () => reject(new Error("That file could not be read as an image."));
      i.src = url;
    });
    const scale = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight));
    if (scale === 1 && file.size <= 1.5 * 1024 * 1024) return file;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.88));
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], file.name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" });
  } finally {
    URL.revokeObjectURL(url);
  }
}

/** Draw the photo and the model's boxes on a canvas. Box coordinates are in original-image pixels. */
export function drawDetection(canvas, imageUrl, detection) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);
      // size the frame and label so they look the same (≈13px text) however large the photo is
      const shown = canvas.getBoundingClientRect().width || img.naturalWidth;
      const k = img.naturalWidth / shown;
      ctx.lineWidth = 3 * k;
      ctx.lineJoin = "round";
      ctx.font = `700 ${13 * k}px "Public Sans", system-ui, sans-serif`;
      for (const r of detection.results || []) {
        // boxes are in the pixels the server analysed; scale if the displayed file differs in size
        const sx = img.naturalWidth / (detection.image_width || img.naturalWidth);
        const sy = img.naturalHeight / (detection.image_height || img.naturalHeight);
        const [x1, y1, x2, y2] = [r.bbox[0] * sx, r.bbox[1] * sy, r.bbox[2] * sx, r.bbox[3] * sy];
        ctx.strokeStyle = "#f0b823";
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        const text = `${r.label} ${Math.round(r.confidence * 100)}%`;
        const padX = 7 * k, h = 24 * k;
        const w = ctx.measureText(text).width + padX * 2;
        const ty = y1 - h < 0 ? y1 : y1 - h;
        const tx = Math.max(0, Math.min(x1 - 1.5 * k, canvas.width - w)); // keep the tag inside the photo
        ctx.fillStyle = "#f0b823";
        ctx.fillRect(tx, ty, w, h);
        ctx.fillStyle = "#0e2a1f";
        ctx.fillText(text, tx + padX, ty + h * 0.7);
      }
      resolve(true);
    };
    img.onerror = () => resolve(false);
    img.src = imageUrl;
  });
}
