@echo off
REM Launches TensorBoard over runs/ so training curves can be watched live
REM while train_multimodal.py (or cross_validate.py --tensorboard) is running.
cd "%~dp0\.."
tensorboard --logdir runs --port 6006
