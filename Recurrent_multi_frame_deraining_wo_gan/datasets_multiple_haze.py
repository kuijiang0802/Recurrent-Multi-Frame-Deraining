### python lib
import os, sys, math, random, glob, cv2
import numpy as np

### torch lib
import torch
import torch.utils.data as data

### custom lib
import utils

class RandomCrop(object):
    def __init__(self, image_size, crop_size):
        self.ch, self.cw = crop_size
        ih, iw = image_size

        self.h1 = random.randint(0, ih - self.ch)
        self.w1 = random.randint(0, iw - self.cw)

        self.h2 = self.h1 + self.ch
        self.w2 = self.w1 + self.cw
        
    def __call__(self, img):
        if len(img.shape) == 3:
            return img[self.h1 : self.h2, self.w1 : self.w2, :]
        else:
            return img[self.h1 : self.h2, self.w1 : self.w2]

class MultiFramesHazeDataset(data.Dataset):

    def __init__(self, opts, dataset, mode):
        super(MultiFramesHazeDataset, self).__init__()

        self.opts = opts
        self.mode = mode
        self.task_videos = []
        self.num_frames = []
        self.dataset_task_list = []

        list_filename = os.path.join(opts.list_dir, "%s_%s.txt" %(dataset, mode))
        print(list_filename)

        with open(list_filename) as f:
            videos = [line.rstrip() for line in f.readlines()]

        for video in videos:
            self.task_videos.append([ os.path.join(video)])
                
            input_dir = os.path.join(self.opts.data_haze_dir, self.mode, "Haze", video)
            frame_list = glob.glob(os.path.join(input_dir, '*.jpg'))

            if len(frame_list) == 0:
                raise Exception("No frames in %s" %input_dir)
                    
            self.num_frames.append(len(frame_list))

        print("[%s] Total %d videos (%d frames)" %(self.__class__.__name__, len(self.task_videos), sum(self.num_frames)))

    def __len__(self):
        return len(self.task_videos)

    def __getitem__(self, index):

        ## random select starting frame index t between [0, N - #sample_frames]
        N = self.num_frames[index]
        T = random.randint(0, N - self.opts.sample_frames)

        video = self.task_videos[index][0]

        ## load input and processed frames
        input_dir = os.path.join(self.opts.data_haze_dir, self.mode, "Rain_Haze", video)
        haze_dir = os.path.join(self.opts.data_haze_dir, self.mode, "Haze", video)
        gt_dir = os.path.join(self.opts.data_haze_dir, self.mode, "GT", video)
        alpha_dir = os.path.join(self.opts.data_haze_dir, self.mode, "Alpha", video)
        trans_dir = os.path.join(self.opts.data_haze_dir, self.mode, "Trans", video)

        ## sample from T to T + #sample_frames - 1
        frame_i = []
        frame_h = []
        frame_a = []
        frame_t = []
        frame_g = []

        for t in range(T+1, T + self.opts.sample_frames+1):
            frame_i.append(utils.read_img(os.path.join(input_dir, "%d.jpg" % t)))
            frame_h.append(utils.read_img(os.path.join(haze_dir, "%d.jpg" % t)))
            frame_a.append(utils.read_img(os.path.join(alpha_dir, "%d.jpg" % t)))
            frame_t.append(utils.read_img(os.path.join(trans_dir, "%d.jpg" % t)))
            frame_g.append(utils.read_img(os.path.join(gt_dir, "%d.jpg" % t)))

        ## data augmentation
        if self.mode == 'train':
            if self.opts.geometry_aug:

                ## random scale
                H_in = frame_i[0].shape[0]
                W_in = frame_i[0].shape[1]

                sc = np.random.uniform(self.opts.scale_min, self.opts.scale_max)
                H_out = int(math.floor(H_in * sc))
                W_out = int(math.floor(W_in * sc))

                ## scaled size should be greater than opts.crop_size
                if H_out < W_out:
                    if H_out < self.opts.crop_size:
                        H_out = self.opts.crop_size
                        W_out = int(math.floor(W_in * float(H_out) / float(H_in)))
                else: ## W_out < H_out
                    if W_out < self.opts.crop_size:
                        W_out = self.opts.crop_size
                        H_out = int(math.floor(H_in * float(W_out) / float(W_in)))

                for t in range(self.opts.sample_frames):
                    frame_i[t] = cv2.resize(frame_i[t], (W_out, H_out))
                    frame_h[t] = cv2.resize(frame_h[t], (W_out, H_out))
                    frame_a[t] = cv2.resize(frame_a[t], (W_out, H_out))
                    frame_t[t] = cv2.resize(frame_t[t], (W_out, H_out))
                    frame_g[t] = cv2.resize(frame_g[t], (W_out, H_out))

            ## random crop
            cropper = RandomCrop(frame_i[0].shape[:2], (self.opts.crop_size, self.opts.crop_size))
            
            for t in range(self.opts.sample_frames):
                frame_i[t] = cropper(frame_i[t])
                frame_h[t] = cropper(frame_h[t])
                frame_a[t] = cropper(frame_a[t])
                frame_t[t] = cropper(frame_t[t])
                frame_g[t] = cropper(frame_g[t])

            if self.opts.geometry_aug:

                ### random rotate
                #rotate = random.randint(0, 3)
                #if rotate != 0:
                #    for t in range(self.opts.sample_frames):
                #        frame_i[t] = np.rot90(frame_i[t], rotate)
                #        frame_p[t] = np.rot90(frame_p[t], rotate)

                ## horizontal flip
                if np.random.random() >= 0.5:
                    for t in range(self.opts.sample_frames):
                        frame_i[t] = cv2.flip(frame_i[t], flipCode=0)
                        frame_h[t] = cv2.flip(frame_h[t], flipCode=0)
                        frame_t[t] = cv2.flip(frame_t[t], flipCode=0)
                        frame_a[t] = cv2.flip(frame_a[t], flipCode=0)
                        frame_g[t] = cv2.flip(frame_g[t], flipCode=0)

            if self.opts.order_aug:
                ## reverse temporal order
                if np.random.random() >= 0.5:
                    frame_i.reverse()
                    frame_h.reverse()
                    frame_a.reverse()
                    frame_t.reverse()
                    frame_g.reverse()
        
        elif self.mode == "test":
            ## resize image to avoid size mismatch after downsampline and upsampling
            H_i = frame_i[0].shape[0]
            W_i = frame_i[0].shape[1]

            H_o = int(math.ceil(float(H_i) / self.opts.size_multiplier) * self.opts.size_multiplier)
            W_o = int(math.ceil(float(W_i) / self.opts.size_multiplier) * self.opts.size_multiplier)

            for t in range(self.opts.sample_frames):
                frame_i[t] = cv2.resize(frame_i[t], (W_o, H_o))
                frame_h[t] = cv2.resize(frame_h[t], (W_o, H_o))
                frame_a[t] = cv2.resize(frame_a[t], (W_o, H_o))
                frame_t[t] = cv2.resize(frame_t[t], (W_o, H_o))
                frame_g[t] = cv2.resize(frame_g[t], (W_o, H_o))
        else:
            raise Exception("Unknown mode (%s)" %self.mode)

        ### convert (H, W, C) array to (C, H, W) tensor
        data = []
        for t in range(self.opts.sample_frames):
            data.append(torch.from_numpy(frame_i[t].transpose(2, 0, 1).astype(np.float32)).contiguous())
            data.append(torch.from_numpy(frame_h[t].transpose(2, 0, 1).astype(np.float32)).contiguous())
            data.append(torch.from_numpy(frame_a[t].transpose(2, 0, 1).astype(np.float32)).contiguous())
            data.append(torch.from_numpy(frame_t[t].transpose(2, 0, 1).astype(np.float32)).contiguous())
            data.append(torch.from_numpy(frame_g[t].transpose(2, 0, 1).astype(np.float32)).contiguous())
        return data
