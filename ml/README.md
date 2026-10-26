# ml/ — model files and training material

| Path | What it is |
|------|------------|
| `weights/best.pt` | **Maize** detector (YOLOv8, classes `MLB` = Maize Leaf Blight, `MSV` = Maize Streak Virus; trained 25 epochs at 640 px on the `maize-leaf-diseases-7` dataset). |
| `weights/cassava.pt` | **Cassava** detector (YOLOv8, 50 epochs at 640 px). Classes: Cassava Bacterial Blight, Cassava Green Mottle, Cassava Mosaic Disease and **Healthy**. |
| `weights/yolov8n.pt` | Pretrained YOLOv8-nano base weights (starting point for training). |
| `labels.json` | Maps each model's class codes to the names farmers see. Add the cassava classes here. |
| `training_samples/` | Sample training-batch images. |
| `legacy/` | Original command-line scripts, kept for reference only. |

## Test a detector on a photo (without starting the website)
```bash
cd backend
python manage.py try_detector ../ml/training_samples/some_leaf.jpg
```
It prints what the model finds at several confidence thresholds. If it finds the disease at 0.25 but not at 0.5,
lower `YOLO_CONF` in `.env`.

## How the website picks the model
Each detector only knows its own crop, so it cannot say "this is not my crop": shown a cassava leaf, the maize model
still answers *Maize Leaf Blight* or *Maize Streak Virus*. The Check-a-plant page therefore defaults to **Auto-detect**:
the server runs every available model on the photo and trusts the one that is most sure (`predict_auto` in
`backend/apps/detection/services/yolo.py`). A farmer can still choose Maize or Cassava by hand.
A new crop you add below is included in Auto-detect automatically.

To see why a photo was read the way it was:
```bash
cd backend
python manage.py try_detector path/to/leaf.jpg        # shows each crop's model and which one wins
```

## Adding or replacing a detector
(Cassava is already in. Use the same steps when you retrain it, or for the next crop.)
1. Train it (ideally 640 px) and copy the best weights to `ml/weights/<crop>.pt`.
2. Open the file's class names (printed by `try_detector`) and add them to `labels.json` under `"cassava"`, for example
   `"CMD": "Cassava Mosaic Disease"`. A 'healthy leaf' class is written `{"name": "Healthy cassava leaf", "healthy": true}` so the app shows it as good news instead of a disease.
3. Restart the backend. The *Cassava* option on the Check-a-plant page becomes selectable.
4. Add translations of the new disease names to `frontend/js/i18n/rw.js` and `fr.js`.

Weight files are small now. If they grow past ~50 MB, move them to Git LFS or GitHub Releases.
