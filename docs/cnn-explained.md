# Convolutional Neural Networks (CNNs) Explained

*A visual guide from pixels to predictions*

---

## The Core Problem

A computer sees an image as a 3D block of numbers — pixel intensities. A 512×512 color X-ray image is actually a grid of 512 × 512 × 3 = **786,432 numbers**, each between 0 and 255.

The challenge: how do you build a system that can look at those ~800K numbers and reliably say "there's a fracture near the wrist"?

You *could* connect every pixel to every neuron in a standard neural network. But for a 512×512 image, even a single hidden layer with 1,000 neurons would require **786 million parameters** just in that layer. Computationally impossible, and it would overfit immediately.

CNNs solve this with three key ideas: **local connectivity**, **weight sharing**, and **pooling**.

---

## Building Blocks

### 1. Convolution: Sliding a Filter Across the Image

Instead of connecting every pixel to every neuron, a CNN uses small **filters** (also called kernels). A filter is typically 3×3 or 5×5 pixels and learns to detect one specific pattern — an edge, a curve, a bright spot.

```
Input image patch:     3×3 Filter:          Dot product:
┌───┬───┬───┐         ┌────┬────┬────┐
│ 10│ 20│ 30│    ×    │ -1 │  0 │ +1 │   = (10×-1)+(20×0)+(30×+1)
│ 40│ 50│ 60│         │ -1 │  0 │ +1 │   + (40×-1)+(50×0)+(60×+1)
│ 70│ 80│ 90│         │ -1 │  0 │ +1 │   + (70×-1)+(80×0)+(90×+1)
└───┴───┴───┘         └────┴────┴────┘   = 60  (vertical edge detected)
```

This filter slides across the entire image — **every position uses the same filter weights**. That's weight sharing: instead of 786K parameters per neuron, a 3×3 filter uses exactly 9 weights, no matter how big the image is.

One filter produces one **feature map** — a 2D activation showing where in the image that pattern was detected. Apply 64 different filters, and you get 64 feature maps.

### 2. ReLU: Throwing Away Negatives

After each convolution, a nonlinear activation function is applied. The most common is **ReLU** (Rectified Linear Unit):

```
  Output
    │         /
    │        /
    │       /
    │      /
    │     /
────┼────/────── Input
    │   /
    0  (negative values → 0)
```

ReLU(x) = max(0, x)

Dead simple. Negative activations → 0. Positive activations → unchanged. Why does this matter? Without a nonlinearity, stacking convolution layers is mathematically equivalent to just one convolution layer. ReLU lets the network learn genuinely complex, nonlinear patterns.

### 3. Pooling: Shrinking the Feature Maps

After convolution + ReLU, **max pooling** downsamples the feature map by taking the maximum value in each small window:

```
Feature map (4×4):       After 2×2 max pooling (stride 2):
┌────┬────┬────┬────┐    ┌────┬────┐
│  1 │  3 │  2 │  4 │    │  3 │  4 │   ← max of each 2×2 region
│  5 │  6 │  1 │  2 │    │  6 │  3 │
│  3 │  2 │  3 │  1 │    └────┴────┘
│  1 │  2 │  1 │  3 │
└────┴────┴────┴────┘
```

Result: feature maps half the width and height, but the dominant activations survive. This achieves:
- **Translation invariance** — a fracture shifted a few pixels still activates the same pooled output
- **Reduced computation** — each subsequent layer processes fewer numbers
- **Larger receptive field** — later layers "see" a bigger chunk of the original image

---

## The Full Architecture

```
┌──────────┐   Conv+ReLU   ┌──────────┐   Pooling   ┌─────────┐   Conv+ReLU   ┌─────────┐
│          │──────────────▶│  Feature │────────────▶│ Feature │──────────────▶│ Feature │
│ Raw X-ray│               │ Maps ×32 │             │Maps ×32 │               │Maps ×64 │
│512×512×3 │               │510×510×32│             │255×255  │               │253×253  │
└──────────┘               └──────────┘             └─────────┘               └─────────┘
                                 │                                                  │
                         "Edges, Blobs"                                    "Textures, Curves"

                                                   ... more Conv+Pool layers ...

                                                        ┌──────────┐
                                                        │ Feature  │  ← Flattened
                                                        │  Maps ×  │    into vector
                                                        │512 depth │
                                                        └────┬─────┘
                                                             │
                                                      Fully Connected
                                                      ┌──────┴──────┐
                                                      │  Classifier  │
                                                      │  (Softmax)   │
                                                      └──────────────┘
                                                      "Fracture" / "Normal"
```

Early layers detect low-level features (edges, intensity gradients). Middle layers combine those into textures and curves. Deep layers detect high-level patterns (bone shapes, fracture patterns). The final fully connected layers take all of that and produce a classification.

---

## How CNNs Learn: Backpropagation

The filter weights start as random numbers. The network makes a prediction, compares it to the correct label, and computes a **loss** (a number representing how wrong it was). Then **backpropagation** computes the gradient of the loss with respect to every weight and nudges each weight in the direction that reduces the loss.

```
Forward pass:   Image → Convolutions → Prediction
                                           │
                                       Loss = how wrong?
                                           │
Backward pass:  ∂Loss/∂weights ← Gradients flow back

Update:         weights = weights - lr × ∂Loss/∂weights
```

This process repeats for every batch of training images, thousands of times. Over 25 epochs × 1,037 batches = 25,925 weight updates, the filters learn to detect exactly the features that matter for fracture detection.

---

## Why Convolutions Work for X-Rays

Three properties make CNNs especially well-suited for medical imaging:

1. **Locality** — a fracture is a local feature; pixels near the fracture are far more relevant than pixels at the image corners. Convolutions exploit this.

2. **Translation invariance** — a wrist fracture looks the same whether it's in the top-left or bottom-right of the frame. Weight sharing + pooling gives this property for free.

3. **Hierarchical features** — a fracture has a specific appearance (cortical disruption, irregular edge, trabecular gap). CNNs learn this hierarchy: edges → bone outline → cortical disruption → fracture.

---

## What a CNN Cannot Do (Alone)

A plain CNN answers: *"Is there a fracture in this image? What class?"*

It does **not** answer: *"Where exactly is the fracture, and draw me a box around it."*

For that, you need an **object detection** architecture — which is what Faster R-CNN (the next document) provides.

---

*Next: [R-CNN, Fast R-CNN, and Faster R-CNN Explained](rcnn-explained.md)*
