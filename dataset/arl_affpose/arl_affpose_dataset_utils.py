import cv2

import numpy as np

import torch
from torch.utils import data
from torch.utils.data import DataLoader, random_split, Subset
from torch.utils.tensorboard import SummaryWriter

import config
from dataset.arl_affpose import arl_affpose_dataset
from dataset import dataset_utils


OBJ_NAMES = ['Missed Detection', 'Mallet','Spatula','Wooden Spoon','Screwdriver','Garden Shovel','Pitcher','Bowl','Mug','Power Drill','Scissors','Large Clamp',]
# We only want to draw the object's pose for one object part.
DRAW_OBJ_PART_POSE = np.array([1, 3, 5, 7, 9, 11, 14, 16, 19, 22, 24])
# We modify the object's pose for visualization.
MODIFY_OBJECT_POSE = np.array([6, 7, 8, 9, 10, 11])
# Class distributions.
OBJ_IDS_DISTRIBUTION = np.array([132/1253, 113/1253, 129/1253, 100/1253, 101/1253, 99/1253, 145/1253, 109/1253, 120/1253, 93/1253, 112/1253])
# Affordance distributions.
AFF_IDS_DISTRIBUTION = np.array([985/2812, 220/2812, 224/2812, 130/2812, 232/2812, 93/2812, 463/2812, 353/2812, 112/2812])


def get_class_weights(logits_size, obj_ids, distribution=OBJ_IDS_DISTRIBUTION):

    class_weights = torch.ones(size=(len(obj_ids), logits_size[0], logits_size[1]), device=config.DEVICE)
    for idx, obj_id in enumerate(obj_ids):
        obj_id = obj_id.item()
        if obj_id > 0:
            # print(f'obj_id: {obj_id - 1}, '
            #       f'weight: {distribution[obj_id - 1]:.3f}'
            #       )
            class_weights[idx, :, :] = 1 / distribution[obj_id-1]
    return class_weights / torch.min(class_weights)

def print_class_obj_names(obj_labels):
    for obj_label in obj_labels:
        _object = map_obj_id_to_name(obj_label)
        print(f"Obj Id:{obj_label}, Object: {_object}")

def print_class_aff_names(aff_labels):
    for aff_label in aff_labels:
        _affordance = map_aff_id_to_name(aff_label)
        print(f"Aff Id:{aff_label}, Affordance: {_affordance}")

def map_obj_id_to_name(object_id):
    if object_id == 0:          # 001_mallet
        return 'bg'
    if object_id == 1:          # 001_mallet
        return 'mallet'
    elif object_id == 2:        # 002_spatula
        return 'spatula'
    elif object_id == 3:        # 003_wooden_spoon
        return 'wooden_spoon'
    elif object_id == 4:        # 004_screwdriver
        return 'screwdriver'
    elif object_id == 5:        # 005_garden_shovel
        return 'garden_shovel'
    elif object_id == 6:        # 019_pitcher_base
        return 'pitcher'
    elif object_id == 7:        # 024_bowl
        return 'bowl'
    elif object_id == 8:        # 025_mug
        return 'mug'
    elif object_id == 9:        # 035_power_drill
        return 'power_drill'
    elif object_id == 10:       # 037_scissors
        return 'scissors'
    elif object_id == 11:       # 051_large_clamp
        return 'large_clamp'
    else:
        print(" --- Object ID:{} does not map to Object Label --- ".format(object_id))
        exit(1)

def map_aff_id_to_name(aff_id):

    if aff_id == 1:
        return 'grasp'
    elif aff_id == 2:
        return 'screw'
    elif aff_id == 3:
        return 'scoop'
    elif aff_id == 4:
        return 'pound'
    elif aff_id == 5:
        return 'support'
    elif aff_id == 6:
        return 'cut'
    elif aff_id == 7:
        return 'wrap-grasp'
    elif aff_id == 8:
        return 'contain'
    elif aff_id == 9:
        return 'clamp'
    else:
        print(" --- Affordance ID:{} does not map to Object Label --- ".format(aff_id))
        exit(1)

def convert_obj_part_mask_to_obj_mask(obj_part_mask):

    obj_part_mask = np.array(obj_part_mask)
    obj_mask = np.zeros((obj_part_mask.shape[0], obj_part_mask.shape[1]), dtype=np.uint8)

    obj_part_ids = np.unique(obj_part_mask)[1:]
    for obj_part_id in obj_part_ids:
        obj_id = map_obj_part_id_to_obj_id(obj_part_id)
        aff_mask_one = np.ones((obj_part_mask.shape[0], obj_part_mask.shape[1]), dtype=np.uint8)
        aff_mask_one = aff_mask_one * obj_id
        obj_mask = np.where(obj_part_mask==obj_part_id, aff_mask_one, obj_mask).astype(np.uint8)
    return obj_mask

def convert_obj_part_mask_to_aff_mask(obj_part_mask):

    obj_part_mask = np.array(obj_part_mask)
    aff_mask = np.zeros((obj_part_mask.shape[0], obj_part_mask.shape[1]), dtype=np.uint8)

    obj_part_ids = np.unique(obj_part_mask)[1:]
    for obj_part_id in obj_part_ids:
        aff_id = map_obj_part_id_to_aff_id(obj_part_id)
        aff_mask_one = np.ones((obj_part_mask.shape[0], obj_part_mask.shape[1]), dtype=np.uint8)
        aff_mask_one = aff_mask_one * aff_id
        aff_mask = np.where(obj_part_mask==obj_part_id, aff_mask_one, aff_mask).astype(np.uint8)
    return aff_mask

def map_obj_id_to_obj_part_ids(object_id):

    if object_id == 0:          # background
        return []
    elif object_id == 1:          # 001_mallet
        return [1, 2]
    elif object_id == 2:        # 002_spatula
        return [3, 4]
    elif object_id == 3:        # 003_wooden_spoon
        return [5, 6]
    elif object_id == 4:        # 004_screwdriver
        return [7, 8]
    elif object_id == 5:        # 005_garden_shovel
        return [9, 10]
    elif object_id == 6:        # 019_pitcher_base
        return [11, 12, 13]
    elif object_id == 7:        # 024_bowl
        return [14, 15]
    elif object_id == 8:        # 025_mug
        return [16, 17, 18]
    elif object_id == 9:        # 035_power_drill
        return [19, 20, 21]
    elif object_id == 10:       # 037_scissors
        return [22, 23]
    elif object_id == 11:       # 051_large_clamp
        return [24, 25]
    else:
        print(" --- Object ID:{} does not map to Object Part IDs --- ".format(object_id))
        exit(1)

def map_obj_id_and_aff_id_to_obj_part_ids(object_id, aff_id):

    if object_id == 1 and aff_id == 1:          # 001_mallet
        return 1
    if object_id == 1 and aff_id == 4:
        return 2
    if object_id == 2 and aff_id == 1:          # 002_spatula
        return 3
    if object_id == 2 and aff_id == 5:
        return 4
    if object_id == 3 and aff_id == 1:          # 003_wooden_spoon
        return 5
    if object_id == 3 and aff_id == 3:
        return 6
    if object_id == 4 and aff_id == 1:          # 004_screwdriver
        return 7
    if object_id == 4 and aff_id == 2:
        return 8
    if object_id == 5 and aff_id == 1:          # 005_garden_shovel
        return 9
    if object_id == 5 and aff_id == 3:
        return 10
    if object_id == 6 and aff_id == 1:          # 019_pitcher_base
        return 11
    if object_id == 6 and aff_id == 7:
        return 12
    if object_id == 6 and aff_id == 8:
        return 13
    if object_id == 7 and aff_id == 7:          # 024_bowl
        return 14
    if object_id == 7 and aff_id == 8:
        return 15
    if object_id == 8 and aff_id == 1:          # 025_mug
        return 16
    if object_id == 8 and aff_id == 7:
        return 17
    if object_id == 8 and aff_id == 8:
        return 18
    if object_id == 9 and aff_id == 1:          # 035_power_drill
        return 19
    if object_id == 9 and aff_id == 2:
        return 20
    if object_id == 9 and aff_id == 5:
        return 21
    if object_id == 10 and aff_id == 1:         # 037_scissors
        return 22
    if object_id == 10 and aff_id == 6:
        return 23
    if object_id == 11 and aff_id == 7:         # 051_large_clamp
        return 24
    if object_id == 11 and aff_id == 9:
        return 25
    else:
        print(" --- Object ID:{} and Aff ID:{} does not map to Object Part IDs --- ".format(object_id, aff_id))
        # exit(1)

def map_obj_part_id_to_obj_id(obj_part_id):

    if obj_part_id == 0:  # 001_mallet
        return 0
    elif obj_part_id in [1, 2]:          # 001_mallet
        return 1
    elif obj_part_id in [3, 4]:        # 002_spatula
        return 2
    elif obj_part_id in [5, 6]:        # 003_wooden_spoon
        return 3
    elif obj_part_id in [7, 8]:        # 004_screwdriver
        return 4
    elif obj_part_id in [9, 10]:       # 005_garden_shovel
        return 5
    elif obj_part_id in [12, 11, 13]: # 019_pitcher_base
        return 6
    elif obj_part_id in [14, 15]:     # 024_bowl
        return 7
    elif obj_part_id in [17, 16, 18]: # 025_mug
        return 8
    elif obj_part_id in [21, 19, 20]: # 035_power_drill
        return 9
    elif obj_part_id in [22, 23]:     # 037_scissors
        return 10
    elif obj_part_id in [24, 25]:     # 051_large_clamp
        return 11
    else:
        print(" --- Object Part ID does not map to Object ID --- ")
        exit(1)

def map_obj_part_id_to_aff_id(obj_part_id):

    if obj_part_id in [1, 3, 5, 7, 9, 11, 16, 19, 22]:  # grasp
        return 1
    elif obj_part_id in [8, 20]:                        # screw
        return 2
    elif obj_part_id in [6, 10]:                        # scoop
        return 3
    elif obj_part_id in [2]:                            # pound
        return 4
    elif obj_part_id in [4, 21]:                        # support
        return 5
    elif obj_part_id in [23]:                           # cut
        return 6
    elif obj_part_id in [12, 14, 17, 24]:               # wrap-grasp
        return 7
    elif obj_part_id in [13, 15, 18]:                   # contain
        return 8
    elif obj_part_id in [25]:                           # clamp
        return 9
    else:
        print(" --- Object Part ID does not map to Affordance ID --- ")
        exit(1)

def colorize_obj_mask(instance_mask):

    instance_to_color = obj_color_map_dict()
    color_mask = np.zeros((instance_mask.shape[0], instance_mask.shape[1], 3), dtype=np.uint8)
    for key in instance_to_color.keys():
        color_mask[instance_mask == key] = instance_to_color[key]

    return np.squeeze(color_mask)

def obj_color_map_dict():
    ''' [red, blue, green]'''

    obj_color_map_dict = {
        0: [0, 0, 0],
        1: [235, 34, 17],   # red
        2: [235, 96, 17],   # orange
        3: [235, 195, 17],  # gold
        4: [176, 235, 17],  # light green/yellow
        5: [76, 235, 17],   # green
        6: [17, 235, 139],  # teal
        7: [17, 235, 225],  # light blue
        8: [17, 103, 235],  # dark blue
        9: [133, 17, 235],  # purple
        10: [235, 17, 215],  # pink
        11: [235, 17, 106],  # hot pink
    }

    return obj_color_map_dict

def obj_color_map(idx):
    # print(f'idx:{idx}')
    ''' [red, blue, green]'''

    if idx == 0:
        return (0, 0, 0)
    elif idx == 1:
        return (235, 34, 17)        # red
    elif idx == 2:
        return (235, 96, 17)        # orange
    elif idx == 3:
        return (235, 195, 17)       # gold
    elif idx == 4:
        return (176,  235, 17)      # light green/yellow
    elif idx == 5:
        return (76,   235, 17)      # green
    elif idx == 6:
        return (17,  235, 139)      # teal
    elif idx == 7:
        return (17,  235, 225)      # light blue
    elif idx == 8:
        return (17,  103, 235)      # dark blue
    elif idx == 9:
        return (133,  17, 235)      # purple
    elif idx == 10:
        return (235, 17, 215)       # pink
    elif idx == 11:
        return (235, 17, 106)       # hot pink
    else:
        print(" --- Object ID:{} does not map to a colour --- ".format(idx))
        exit(1)

def colorize_aff_mask(instance_mask):

    instance_to_color = aff_color_map_dict()
    color_mask = np.zeros((instance_mask.shape[0], instance_mask.shape[1], 3), dtype=np.uint8)
    for key in instance_to_color.keys():
        color_mask[instance_mask == key] = instance_to_color[key]

    return np.squeeze(color_mask)

def aff_color_map_dict():
    ''' [red, blue, green]'''

    aff_color_map_dict = {
        0: [0, 0, 0],
        1: [133, 17, 235],  # grasp: purple
        2: [235, 96, 17],   # screw: orange
        3: [235, 195, 17],  # scoop: yellow/gold
        4: [176, 235, 17],  # pound: light green/yellow
        5: [76, 235, 17],   # support: green
        6: [17, 235, 139],  # cut: teal
        7: [17, 235, 225],  # wrap-grasp: light blue
        8: [17, 103, 235],  # contain: dark blue
        9: [235, 34, 17],   # clamp: red
    }

    return aff_color_map_dict


def aff_color_map(idx):
    ''' [red, blue, green]'''

    if idx == 1:
        return (133, 17, 235)   # grasp: purple
    elif idx == 2:
        return (235, 96, 17)    # screw: orange
    elif idx == 3:
        return (235, 195, 17)   # scoop: yellow/gold
    elif idx == 4:
        return (176, 235, 17)   # pound: light green/yellow
    elif idx == 5:
        return (76, 235, 17)    # support: green
    elif idx == 6:
        return (17, 235, 139)   # cut: teal
    elif idx == 7:
        return (17, 235, 225)   # wrap-grasp: light blue
    elif idx == 8:
        return (17, 103, 235)   # contain: dark blue
    elif idx == 9:
        return (235, 34, 17)    # clamp: red
    else:
        print(" --- Affordance ID:{} does not map to a colour --- ".format(idx))
        exit(1)

def format_obj_ids_to_aff_ids_list(object_ids, gt_object_part_ids):
    '''Function used to map predicted object ids to aff ids in Affordnace Net.

    Args:
        object_ids: TODO: Check if this list is empty.
    '''
    aff_ids, obj_part_ids = [], []
    for idx, object_id in enumerate(object_ids):
        object_part_ids = map_obj_id_to_obj_part_ids(object_id)
        _aff, _obj_part = [], []
        for object_part_id in object_part_ids:
            if object_part_id in gt_object_part_ids:
                _obj_part.append(object_part_id)
                _aff.append(map_obj_part_id_to_aff_id(object_part_id))
        obj_part_ids.append(_obj_part)
        aff_ids.append(_aff)
    return obj_part_ids, aff_ids

def map_obj_ids_to_aff_ids_list(object_ids):
    aff_ids, obj_part_ids = [], []
    for object_id in object_ids:
        _obj_part = []
        object_part_ids = map_obj_id_to_obj_part_ids(object_id)
        for object_part_id in object_part_ids:
            _obj_part.append(map_obj_part_id_to_aff_id(object_part_id))
            # _object_part_ids_list.append(object_part_id)
        obj_part_ids.append(object_part_ids)
        aff_ids.append(_obj_part)
    return obj_part_ids, aff_ids

def get_obj_binary_masks(image, obj_ids, obj_part_ids, aff_binary_masks):

    height, width = image.shape[:2]
    obj_binary_masks = np.zeros((len(obj_ids), height, width), dtype=np.uint8)

    for obj_part_idx, obj_part_id in enumerate(obj_part_ids):
        obj_id = map_obj_part_id_to_obj_id(obj_part_id)
        obj_idx = np.argwhere(obj_id == obj_ids)[0][0]
        obj_binary_masks[obj_idx, :, :] += np.array(aff_binary_masks[obj_part_idx, :, :], dtype=np.uint8)
        # debug
        # print(f'obj_idx:{obj_idx},\tobj_id: {obj_id},\tobj_ids: {obj_ids}')
        # cv2.imshow('obj_binary_mask', obj_binary_masks[obj_idx, :, :] * 20)
        # cv2.waitKey(0)

    return obj_binary_masks

def get_obj_part_mask(image, obj_part_ids, aff_binary_masks):

    height, width = image.shape[:2]
    instance_masks = np.zeros((height, width), dtype=np.uint8)
    instance_mask_one = np.ones((height, width), dtype=np.uint8)

    for idx, obj_part_id in enumerate(obj_part_ids):
        aff_binary_mask = np.array(aff_binary_masks[idx, :, :], dtype=np.uint8)

        instance_mask = instance_mask_one * obj_part_id
        instance_masks = np.where(aff_binary_mask, instance_mask, instance_masks).astype(np.uint8)

    return instance_masks

def draw_bbox_on_img(image, obj_ids, boxes, color=(255, 255, 255), scores=None):
    bbox_img = image.copy()

    if scores is None:
        for obj_id, bbox in zip(obj_ids, boxes):
            bbox = dataset_utils.format_bbox(bbox)
            # see dataset_utils.get_bbox for output of bbox.
            # x1,y1 ------
            # |          |
            # |          |
            # |          |
            # --------x2,y2
            bbox_img = cv2.rectangle(bbox_img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), 255, 1)

            cv2.putText(bbox_img,
                        f'{map_obj_id_to_name(obj_id)}',
                        (bbox[0], bbox[1] - 5),
                        cv2.FONT_ITALIC,
                        0.6,
                        color)
    else:
        for score, obj_id, bbox in zip(scores, obj_ids, boxes):
            bbox = dataset_utils.format_bbox(bbox)
            # see dataset_utils.get_bbox for output of bbox.
            # x1,y1 ------
            # |          |
            # |          |
            # |          |
            # --------x2,y2
            bbox_img = cv2.rectangle(bbox_img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), 255, 1)

            cv2.putText(bbox_img,
                        f'{map_obj_id_to_name(obj_id)}: {score:.3f}',
                        (bbox[0], bbox[1] - 5),
                        cv2.FONT_ITALIC,
                        0.6,
                        color)

    return bbox_img

def get_segmentation_masks(image, obj_ids, binary_masks):

    height, width = image.shape[0], image.shape[1]
    instance_masks = np.zeros((height, width), dtype=np.uint8)
    instance_mask_one = np.ones((height, width), dtype=np.uint8)

    if len(binary_masks.shape) == 2:
        binary_masks = binary_masks[np.newaxis, :, :]

    for idx, obj_id in enumerate(obj_ids):
        binary_mask = binary_masks[idx, :, :]
        instance_mask = instance_mask_one * obj_id
        instance_masks = np.where(binary_mask, instance_mask, instance_masks).astype(np.uint8)

    return instance_masks

def format_target_data(image, target):
    height, width = image.shape[0], image.shape[1]

    # original mask and binary masks.
    target['obj_mask'] = np.array(target['obj_mask'], dtype=np.uint8).reshape(height, width)
    target['obj_binary_masks'] = np.array(target['obj_binary_masks'] > config.MASK_THRESHOLD, dtype=np.uint8).reshape(-1, height, width)
    target['aff_mask'] = np.array(target['aff_mask'], dtype=np.uint8).reshape(height, width)
    target['aff_binary_masks'] = np.array(target['aff_binary_masks'] > config.MASK_THRESHOLD, dtype=np.uint8).reshape(-1, height, width)
    target['obj_part_mask'] = np.array(target['obj_part_mask'], dtype=np.uint8).reshape(height, width)

    # ids and bboxs.
    target['obj_ids'] = np.array(target['obj_ids'], dtype=np.int32).flatten()
    target['obj_boxes'] = np.array(target['obj_boxes'], dtype=np.int32).reshape(-1, 4)
    target['aff_ids'] = np.array(target['aff_ids'], dtype=np.int32).flatten()
    target['obj_part_ids'] = np.array(target['obj_part_ids'], dtype=np.int32).flatten()

    # depth images.
    target['depth_8bit'] = np.squeeze(np.array(target['depth_8bit'], dtype=np.uint8))
    target['depth_16bit'] = np.squeeze(np.array(target['depth_16bit'], dtype=np.uint16))
    # target['masked_depth_16bit'] = np.squeeze(np.array(target['masked_depth_16bit'], dtype=np.uint16))

    return target