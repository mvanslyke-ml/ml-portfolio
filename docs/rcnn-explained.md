# From R-CNN to Faster R-CNN: Object Detection Explained

*How we went from "classify images" to "find and label every object with a box"*

---

## The Detection Problem

A CNN can tell you "this X-ray contains a fracture." But a useful medical tool needs to tell you **where** — and ideally draw a box around the exact location.

This is **object detection**: given an image, output a list of (bounding box, class, confidence) tuples. The challenge is that a fracture can appear anywhere in a 512×512 X-ray, at any scale, at any angle.

The R-CNN family solved this problem in three generations, each dramatically faster and more accurate than the last.

---

## Generation 1: R-CNN (2014)

*Regions with Convolutional Neural Networks*

**Core idea:** Use a classical algorithm (Selective Search) to propose ~2,000 candidate regions that might contain an object. Run a CNN on each region independently. Classify each one.

```
                 ┌─────────────────────────────────────────────┐
                 │              Original Image                  │
                 └───────────────────┬─────────────────────────┘
                                     │
                            Selective Search
                         (classical image algorithm)
                                     │
                    ~2,000 proposed regions (crops)
                                     │
              ┌──────────┬───────────┼───────────┬──────────┐
              ▼          ▼           ▼            ▼          ▼
           ┌─────┐    ┌─────┐    ┌─────┐      ┌─────┐   ┌─────┐
           │ CNN │    │ CNN │    │ CNN │  ...  │ CNN │   │ CNN │
           └──┬──┘    └──┬──┘   └──┬──┘      └──┬──┘   └──┬──┘
              │           │         │              │          │
           SVM Classifier + Bounding Box Regressor per region
              │
       "Fracture 87%" / "Background"
```

**The problem:** Running a full CNN on 2,000 crops per image is brutally slow — ~47 seconds per image at test time. Also, the CNN, SVM, and bounding box regressor are all trained separately (not end-to-end).

---

## Generation 2: Fast R-CNN (2015)

**Core idea:** Stop running the CNN 2,000 times. Run the CNN *once* on the whole image to produce a single feature map, then project the proposed regions onto that shared feature map.

```
┌────────────────────────────────────────────┐
│              Original Image                │──── Selective Search ──▶ ~2000 region proposals
└───────────────────┬────────────────────────┘              │
