---
title: AI-Powered Bone Fracture Detection
id: fracture-detector
date: Apr 2026
category: ml, cv, deploy
tags: Deep Learning, Computer Vision, PyTorch, Faster R-CNN, Medical AI, AWS SageMaker, LIVE
github: https://github.com/mvanslyke-ml/ml-portfolio
demo_url: https://api.mvanslyke-ml.com/fracture-detector
demo_description: Upload an X-ray image to detect and localize bone fractures with bounding boxes (powered by AWS SageMaker Serverless)
article: https://mvanslyke-ml.com/blog/bone-fracture-detection
metrics:
  mAP@0.5:0.95: "0.5861 (5-fold CV mean)"
  Architecture: Faster R-CNN
  Backbone: ResNet50 FPN V2
  Classes: 7 Fracture Types
  Training Images: "4,148 X-rays"
  Deployment: AWS SageMaker Serverless
---

## What This Project Does

This system analyzes X-ray images of upper extremities (hands, wrists, forearms) and automatically identifies whether a bone fracture is present — and if so, draws a bounding box around the fracture and classifies what type of fracture it is.

Think of it as a second-opinion tool that a radiologist or ER physician could use to catch fractures that might be subtle or easy to miss under a busy workload.

---

## The Problem

Radiologists in busy emergency departments review hundreds of X-rays per shift. Hairline fractures and minor breaks are the most commonly missed injuries — not from lack of skill, but from volume and fatigue. An automated detection system that flags potential fractures in real time can meaningfully reduce diagnostic errors.

---

## The Model

The model is built on **Faster R-CNN with a ResNet50 FPN V2 backbone** — a well-established architecture in the object detection field that was chosen for its balance of accuracy and inference speed.

### What that means in plain terms:
- **Faster R-CNN** is a two-stage detector: it first proposes candidate regions in the image that might contain something interesting, then classifies each region. This makes it more accurate than single-shot detectors at the cost of slightly more computation.
- **ResNet50 FPN V2** is a backbone network that extracts visual features at multiple scales simultaneously — good at detecting both large and small fractures in the same image.

### Custom modifications:
- **Anchor generator tuned for fractures** — the default anchor sizes are designed for everyday objects; fractures are smaller and more elongated, so anchor sizes and aspect ratios were customized specifically for X-ray anatomy.
- **Deeper RPN head** — the region proposal network (the part that finds candidate fracture locations) was deepened with additional layers to give it more capacity to recognize subtle fracture patterns.

---

## Training Approach

| Component | Choice | Why |
|---|---|---|
| Training strategy | 5-fold cross validation | Ensures no single lucky train/test split inflates results |
| Weight averaging | Exponential Moving Average (EMA) | Smooths training noise; final weights generalize better than the last epoch alone |
| Precision | Mixed precision (FP16 + FP32) | ~2× faster training without loss of model quality |
| Learning rate | Cosine schedule with warmup | Avoids early instability; anneals smoothly to convergence |
| Class balancing | Weighted random sampler | Fracture images are rarer than healthy ones; prevents the model from defaulting to "no fracture" |
| Augmentation | Contrast, sharpness, flip, rotation, color jitter | Simulates real-world variation in X-ray exposure and positioning |
| Batch size | 4 images | Constrained by GPU VRAM; compensated by gradient accumulation |

---

## Results

Evaluated using **mAP@0.5:0.95** (mean Average Precision at IoU thresholds from 0.5 to 0.95, the COCO standard). This is a strict metric — a prediction only counts if the bounding box overlaps the ground truth by at least 50–95%.

### 5-Fold Cross-Validation

| Fold | Best mAP@0.5:0.95 | Best Epoch |
|------|-------------------|------------|
| 1    | 0.6066            | 24         |
| 2    | 0.5747            | 25         |
| 3    | 0.5762            | ~23        |
| 4    | 0.6076            | —          |
| 5    | 0.5656            | —          |
| **Mean** | **0.5861 ± 0.018** | — |

Each fold trained for **25 epochs** on ~3,318 images and validated on ~830 images. Training ran on a Kaggle GPU (NVIDIA T4) with approximately 4.5 hours per fold.

### Learning Curve (Fold 1)

Loss fell steadily from 0.286 at epoch 1 to 0.039 at epoch 25. mAP improved from 0.115 to a peak of **0.6066** at epoch 24, with no sign of overfitting (validation mAP continued trending upward through the final epochs).

### Final Model

After cross-validation, a final model was trained on all **4,148 training images** for 25 epochs. Final epoch loss: **0.0396**. This is the model that is deployed in the live demo.

---

## Fracture Categories

The model classifies detections into **7 fracture types** based on anatomical location and fracture pattern (background is handled internally by the detector and not counted as a class). Categories span common upper extremity fracture patterns seen in emergency imaging.

---

## Live Demo

The demo is powered by a serverless AWS SageMaker endpoint — meaning there is no server running idle between requests. When you submit an X-ray:

1. Your image is sent to an AWS Lambda function in your browser
2. Lambda forwards it to the SageMaker endpoint, which loads the model on demand
3. The model runs inference and returns bounding boxes + fracture type labels
4. Results are displayed with confidence scores

**Note on cold starts:** If the endpoint hasn't been used recently, the first request takes 15–30 seconds to spin up. Subsequent requests are fast.

---

## Technical Stack

**Model & Training:**
- PyTorch + TorchVision
- Custom `AnchorGenerator` and `RPNHead`
- Mixed precision via `torch.cuda.amp`
- EMA via `torch.optim.swa_utils.AveragedModel`
- 5-fold CV with `sklearn.model_selection.KFold`
- Dataset: [Fracture Multi-Region X-ray Data](https://www.kaggle.com/datasets/bmadushanirodrigo/fracture-multi-region-x-ray-data) (4,148 labeled images)

**Infrastructure:**
- Model weights packaged and stored on AWS S3
- Served via AWS SageMaker Serverless Inference (scales to zero, pay-per-request)
- Browser → API Gateway → Lambda proxy → SageMaker → response

---

## Limitations & Honest Caveats

- This is a **research prototype**, not a clinical tool. It has not been validated against clinical ground truth at scale.
- Performance degrades on X-ray images with unusual positioning, heavy metal implants, or image quality outside the training distribution.
- The model was trained on a public dataset; a production clinical system would require training on hospital-grade, de-identified DICOM data with radiologist-verified labels.
- Serverless cold starts (15–30 s) make the demo unsuitable for time-sensitive clinical workflows.

---

## Future Work

- Expand anatomical coverage to lower extremities (femur, tibia, ankle)
- Add severity grading (displaced vs. non-displaced, comminuted)
- Fine-tune on external validation datasets
- Integrate DICOM input support for direct PACS compatibility
- Request SageMaker quota increase to 6,144 MB for faster cold start + inference

---

*This project demonstrates that modern deep learning can be deployed affordably and accessibly for medical imaging tasks — even on a personal portfolio budget, with no idle server costs.*
