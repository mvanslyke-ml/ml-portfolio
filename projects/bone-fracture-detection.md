---
title: AI-Powered Bone Fracture Detection
date: Feb 2026
category: ml, cv, deploy
tags: Deep Learning, Computer Vision, PyTorch, Faster R-CNN, Medical AI, LIVE
github: https://github.com/mvanslyke-ml/ml-portfolio/projects/bone-fracture-detection
demo_url: https://api.mvanslyke-ml.com/fracture-detector
demo_description: Upload an X-ray image to detect and localize bone fractures with bounding boxes (powered by SageMaker Serverless Inference)
article: https://mvanslyke-ml.com/blog/bone-fracture-detection
metrics:
  Accuracy: 88.6%
  Loss: 11.4%
  Model: ResNet50 FPN
  Training Time: 1 week
---

## Overview

Developed a deep learning system to detect and localize bone fractures in X-ray images of upper extremities using Faster R-CNN with ResNet50 FPN V2 backbone. The model achieved 88.6% accuracy, exceeding the initial 85% target.

## Problem Statement

Medical facilities process thousands of X-rays daily. Accurate fracture identification is challenging, especially for trainees and in emergency settings. Small hairline fractures can be easily missed, yet timely detection is critical for proper treatment.

## Solution

Built a production-grade AI system using:

- **Model**: Faster R-CNN with ResNet50 FPN V2 backbone
- **Training**: 5 epochs on 3,000+ annotated X-ray images  
- **Optimization**: Aggressive data augmentation for real-world robustness
- **Deployment**: Interactive demo on Hugging Face Spaces

## Key Results

The model successfully:
- Achieved 88.6% accuracy (11.4% loss)
- Detects multiple fractures per image
- Provides precise bounding box localization
- Classifies fracture types across 7 categories

## Technical Approach

### Data Augmentation

Implemented multiple augmentation techniques to simulate real-world conditions:
- Random AutoContrast (10%)
- Random Sharpness (10%)
- Random Horizontal Flip (10%)
- Random Inversion (10%)
- Random Erasing (10%)

### Model Comparison

Trained and compared 4 model variants:
1. Faster R-CNN + ResNet50 FPN
2. **Faster R-CNN + ResNet50 FPN V2** (Winner - 11.4% loss)
3. Faster R-CNN + MobileNet V3 Large
4. Faster R-CNN + MobileNet V3 Large 320

ResNet50 FPN V2 offered the best balance of accuracy and inference speed.

## Real-World Impact

### For Medical Professionals
- **Second Opinion Tool**: Automated verification system
- **Triage Support**: Prioritize urgent cases in busy ERs
- **Training Aid**: Educational tool for medical students

### For Healthcare Systems
- **Faster Diagnosis**: Reduced time from imaging to treatment
- **Error Reduction**: Catch subtle fractures that might be missed
- **Cost Efficiency**: Optimize specialist consultation time

## Live Demo

Try the interactive demo on Hugging Face Spaces:
- Upload X-ray images (JPEG, PNG)
- Real-time fracture detection with bounding boxes
- Confidence scores for each prediction
- Support for multiple fractures per image

## Technical Stack

**Languages & Frameworks:**
- Python 3.10
- PyTorch & TorchVision
- OpenCV
- Streamlit (demo interface)

**Training Infrastructure:**
- Kaggle GPU acceleration
- Adam optimizer (learning rate: 0.0001)
- Batch size: 12
- 5 training epochs
- Cross-entropy loss + IoU for bounding boxes

**Model Architecture:**
- Backbone: ResNet50 FPN V2
- Detection head: Faster R-CNN
- 7 output classes (background is handled internally by the detector)

## Challenges & Solutions

### Challenge 1: Computational Constraints
**Problem**: GPU memory limitations on Kaggle's free tier  
**Solution**: Split training across sessions, careful CUDA cache management

### Challenge 2: Dataset Idealization
**Problem**: Training data too perfect, risk of overfitting  
**Solution**: Aggressive augmentation to simulate real-world imperfections

### Challenge 3: Bounding Box Precision
**Problem**: Achieving optimal IoU scores  
**Solution**: Hyperparameter tuning and validation on diverse X-ray angles

## Future Work

### Short-Term
- Fine-tuning with COCO framework
- False positive optimization
- Expanded testing on external datasets

### Long-Term
- Broader anatomical coverage (legs, spine, ribs)
- Integration with hospital PACS systems
- Severity classification
- Real-time model retraining pipeline
- Multi-language support for global deployment

## Key Learnings

1. **Domain Knowledge is Critical**: Understanding medical imaging constraints shaped design decisions
2. **Augmentation Strategy Matters**: Simulate real-world conditions, not just increase data volume
3. **Model Selection is a Trade-off**: The "best" model balances accuracy, speed, and maintainability
4. **Proof of Concept ≠ Production**: Significant work remains for clinical deployment

## Impact Metrics

- **Accuracy Target**: 85% → **Achieved**: 88.6% ✅
- **Training Time**: 1 week
- **Dataset**: 3,000+ annotated images
- **Inference Speed**: ~2-3 seconds per image
- **Model Variants Tested**: 4

## Resources

- **GitHub**: Full code, notebooks, model weights
- **Hugging Face**: Interactive demo
- **Kaggle Dataset**: Bone fracture detection dataset
- **Research Paper**: Technical methodology and results
- **Presentation**: Project overview slides

---

*This project demonstrates the application of computer vision and deep learning to real-world medical challenges. The model serves as a proof-of-concept for AI-assisted diagnostic tools that could, with further development, make a meaningful difference in patient care.*
