# ml/ — model files and training material

| Path | What it is |
|------|------------|
| `weights/best.pt` | Trained YOLOv8 maize-disease model. **This is the file the backend loads.** |
| `weights/yolov8n.pt` | Pretrained YOLOv8-nano base weights (starting point for training; can be re-downloaded by `ultralytics`). |
| `training_samples/` | Sample training-batch images produced by YOLO (useful for the report/presentation). |
| `legacy/` | Original command-line scripts, kept for reference only. They are **not** used by the web app. |

## Notes
- The backend reads the model path from `YOLO_MODEL_PATH` (default `ml/weights/best.pt`).
- `legacy/maizediseases.py` imports `db.db` (the old MySQL login code), which was never in the repository, so it will not run as-is.
- `legacy/weather_advisor.py` was ported into `backend/apps/advisory/services/`.
- Retrained a better model? Replace `weights/best.pt` in its own pull request and say what changed (dataset, epochs, accuracy). If weight files grow past ~50 MB, move them to Git LFS or GitHub Releases.
