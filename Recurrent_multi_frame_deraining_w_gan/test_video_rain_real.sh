CUDA_VISIBLE_DEVICES=5 python test_video_rain_real.py -method MultiShareTransformNet_B5_nf32_IN_T7_W3_D1_C1_I1_sh_0512_full_skip_s2_sgan_tv_pw128_L2Loss_a50.0_wST0_wHT0_wVGG0_L12_ADAM_lr0.0001_off20_step20_drop0.5_min1e-05_es100_bs2 -epoch 0 -dataset rain_removal -task RainRemoval/original -data_dir data_practical

