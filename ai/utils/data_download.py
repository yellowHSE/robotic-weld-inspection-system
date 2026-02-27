from ultralytics.hub import load_dataset

# Ultralytics HUB에서 데이터셋 다운로드
dataset = load_dataset("https://hub.ultralytics.com/datasets/the-welding-defect-dataset-v2")
print(f"데이터셋 저장 경로: {dataset.path}")