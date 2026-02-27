from ultralytics import YOLO

# best.pt 로드
model = YOLO("best.pt")

# 이미지 예측
results = model.predict(
    "test_image.jpg",  # 예측할 이미지
    save=True,         # 결과 이미지 저장
    show=True          # 결과 이미지 화면 표시
)

# 클래스 이름 + 확률 확인
for r in results:
    boxes = r.boxes
    for cls, score in zip(boxes.cls, boxes.conf):
        print(f"{model.names[int(cls)]}: {score:.2f}")  # 예: Good: 0.95