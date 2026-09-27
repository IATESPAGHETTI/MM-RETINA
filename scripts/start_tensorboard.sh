#!/usr/bin/env bash
# Launches TensorBoard over runs/ so training curves can be watched live
# while train_multimodal.py (or cross_validate.py --tensorboard) is running.
cd "$(dirname "$0")/.." || exit 1
tensorboard --logdir runs --port 6006
