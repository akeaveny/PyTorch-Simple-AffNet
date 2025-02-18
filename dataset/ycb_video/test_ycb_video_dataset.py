import unittest

import numpy as np

import cv2

import torch
from torch.utils import data

import sys
sys.path.append('../../')

import config

from dataset.ycb_video import ycb_video_dataset
from dataset.ycb_video import ycb_video_dataset_utils

class YCBVideoDatasetTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(YCBVideoDatasetTest, self).__init__(*args, **kwargs)

        # Load ARL AffPose dataset.
        dataset = ycb_video_dataset.YCBVideoPoseDataset(
            dataset_dir=config.YCB_DATASET_ROOT_PATH,
            image_path_txt_file=config.YCB_TRAIN_FILE,
            image_domain=config.YCB_IMAGE_DOMAIN,
            mean=config.YCB_IMAGE_MEAN,
            std=config.YCB_IMAGE_STD,
            resize=config.YCB_RESIZE,
            crop_size=config.YCB_CROP_SIZE,
            is_train=True,
        )

        # create dataloader.
        self.data_loader = torch.utils.data.DataLoader(dataset, batch_size=1, shuffle=False)
        print(f'Selecting {len(self.data_loader)} images ..')

    def test_maskrcnn_dataloader(self):
        print('\nVisualizing Ground Truth Data for MaskRCNN ..')
        # loop over dataset.
        for i, (image, target) in enumerate(self.data_loader):
            # print(f'\n{i}/{len(self.data_loader)} ..')

            # format data.
            image = np.squeeze(np.array(image)).transpose(1, 2, 0)
            image = np.array(image * (2 ** 8 - 1), dtype=np.uint8)
            image, target = ycb_video_dataset_utils.format_target_data(image, target)

            # Bounding Box.
            bbox_img = ycb_video_dataset_utils.draw_bbox_on_img(image=image,
                                                                obj_ids=target['obj_ids'],
                                                                boxes=target['obj_boxes'],
                                                                )

            # Original Segmentation Mask.
            color_mask = ycb_video_dataset_utils.colorize_obj_mask(target['obj_mask'])
            color_mask = cv2.addWeighted(bbox_img, 0.35, color_mask, 0.65, 0)

            # Binary Masks.
            binary_mask = ycb_video_dataset_utils.get_segmentation_masks(image=image,
                                                                         obj_ids=target['obj_ids'],
                                                                         binary_masks=target['obj_binary_masks'],
                                                                         )
            color_binary_mask = ycb_video_dataset_utils.colorize_obj_mask(binary_mask)
            color_binary_mask = cv2.addWeighted(bbox_img, 0.35, color_binary_mask, 0.65, 0)

            # print object and affordance class names.
            ycb_video_dataset_utils.print_class_obj_names(target['obj_ids'])

            # show plots.
            # cv2.imshow('rgb', cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            # cv2.imshow('bbox', cv2.cvtColor(bbox_img, cv2.COLOR_BGR2RGB))
            # cv2.imshow('mask', cv2.cvtColor(color_mask, cv2.COLOR_BGR2RGB))
            # cv2.imshow('binary_mask', cv2.cvtColor(color_binary_mask, cv2.COLOR_BGR2RGB))
            # cv2.waitKey(1)

    def test_affnet_dataloader(self):
        print('\nVisualizing Ground Truth Data for AffNet ..')

        # loop over dataset.
        for i, (image, target) in enumerate(self.data_loader):
            print(f'\n{i}/{len(self.data_loader)} ..')

            # format data.
            image = np.squeeze(np.array(image)).transpose(1, 2, 0)
            image = np.array(image * (2 ** 8 - 1), dtype=np.uint8)
            image, target = ycb_video_dataset_utils.format_target_data(image, target)

            # Bounding Box.
            bbox_img = ycb_video_dataset_utils.draw_bbox_on_img(image=image,
                                                                obj_ids=target['obj_ids'],
                                                                boxes=target['obj_boxes'],
                                                                )

            # Original Segmentation Mask.
            color_mask = ycb_video_dataset_utils.colorize_aff_mask(target['aff_mask'])
            color_mask = cv2.addWeighted(bbox_img, 0.35, color_mask, 0.65, 0)

            # Binary Masks.
            binary_mask = ycb_video_dataset_utils.get_segmentation_masks(image=image,
                                                                         obj_ids=target['aff_ids'],
                                                                         binary_masks=target['aff_binary_masks'],
                                                                         )
            color_binary_mask = ycb_video_dataset_utils.colorize_aff_mask(binary_mask)
            color_binary_mask = cv2.addWeighted(bbox_img, 0.35, color_binary_mask, 0.65, 0)

            # # show object mask derived from affordance masks.
            # obj_part_mask = ycb_video_dataset_utils.get_obj_part_mask(image=image,
            #                                                              obj_ids=target['obj_ids'],
            #                                                              aff_ids=target['aff_ids'],
            #                                                              bboxs=target['obj_boxes'],
            #                                                              binary_masks=target['aff_binary_masks'],
            #                                                              )
            #
            # obj_mask = ycb_video_dataset_utils.convert_obj_part_mask_to_obj_mask(obj_part_mask)
            # color_obj_mask = ycb_video_dataset_utils.colorize_obj_mask(obj_mask)
            # color_obj_mask = cv2.addWeighted(bbox_img, 0.35, color_obj_mask, 0.65, 0)

            # show plots.
            cv2.imshow('rgb', cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            cv2.imshow('bbox', cv2.cvtColor(bbox_img, cv2.COLOR_BGR2RGB))
            cv2.imshow('mask', cv2.cvtColor(color_mask, cv2.COLOR_BGR2RGB))
            cv2.imshow('binary_mask', cv2.cvtColor(color_binary_mask, cv2.COLOR_BGR2RGB))
            # cv2.imshow('obj_mask', cv2.cvtColor(color_obj_mask, cv2.COLOR_BGR2RGB))
            cv2.waitKey(0)

if __name__ == '__main__':
    # unittest.main()

    # run desired test.
    suite = unittest.TestSuite()
    suite.addTest(YCBVideoDatasetTest("test_affnet_dataloader"))
    runner = unittest.TextTestRunner()
    runner.run(suite)

