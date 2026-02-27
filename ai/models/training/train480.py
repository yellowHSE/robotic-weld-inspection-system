from ultralytics import YOLO
import torch

def train_model():
    # 1. 모델 로드 (보고서대로 사전 학습된 yolov8s 사용) [cite: 104]
    model = YOLO("yolov8s.pt")

    # 2. 학습 실행 (보고서 4.3절 파라미터 적용) [cite: 98]
    model.train(
        data="welding.yaml",   # 위에서 만든 설정 파일
        epochs=150,            # 보고서 설정값 [cite: 109]
        imgsz=480,             # 첫 번째 실험 해상도 [cite: 110]
        batch=32,              # 640px 기준 권장 배치 [cite: 111]
        optimizer="SGD",       # 보고서 명시 옵티마이저 [cite: 112]
        lr0=0.01,              # 초기 학습률 [cite: 113]
        device=0,              # RTX 4060 SUPER 사용 
        project="welding_project",
        name="resolution_640"
    )

    # 3. 검증 수행 [cite: 115]
    metrics = model.val()
    print(f"학습 완료! 결과 지표: {metrics}")

if __name__ == "__main__":
    train_model()