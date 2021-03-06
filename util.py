
import os
import numpy as np
from PIL import Image
from skimage.transform import resize
from skimage.measure import label, regionprops

import glob
import cv2
import os


def create_dir(dirname):
    try:
        os.mkdir(dirname)
        return True
    except OSError:
        return False


def to_numpy(tensor):
    return tensor.detach().cpu().numpy()


def save_to_tif(path, data):
    with open(path, 'wb') as f:
        np.save(f, data, allow_pickle=True)


def load_image(path, is_mask):
    if not is_mask:
        return np.asarray(Image.open(path).convert("RGB"))
    else:
        return np.asarray(Image.open(path).convert('L'))


def load_bboxs(path):
    bboxs = []
    classes = ['BE', 'suspicious', 'HGD', 'cancer', 'polyp']

    with open(path, 'r') as f:
        lines = f.readlines()

        for line in lines:
            line = line.split(' ')
            x, y, xmax, hmax, class_ = int(line[0]), int(
                line[1]), int(line[2]), int(line[3]), line[4][:-1]
            label = classes.index(class_)
            bboxs.append((label, (x, y, xmax, hmax)))

    return bboxs


def save_bboxs(path, bboxs):
    classes = ['BE', 'suspicious', 'HGD', 'cancer', 'polyp']

    with open(path, 'w') as f:
        for bbox in bboxs:
            label, values = bbox
            bbox_str = ' '.join([str(value)
                                 for value in values]) + ' ' + classes[label]
            f.write(bbox_str + '\n')


def load_set(folder, is_mask, shuffle=False):
    data = []
    img_list = sorted(glob.glob(os.path.join(folder, '*.png')) +
                      glob.glob(os.path.join(folder, '*.jpg')) +
                      glob.glob(os.path.join(folder, '*.tif')) +
                      glob.glob(os.path.join(folder, '*.jpeg')))
    if shuffle:
        np.random.shuffle(img_list)
    for img_fn in img_list:
        img = load_image(img_fn, is_mask)
        data.append(img)
    return data, img_list


def compute_bboxs_from_masks(masks):
    # input (5, 224, 224)
    bboxs = []
    for lab, mask in enumerate(masks):
        regions = label(mask)
        props = regionprops(regions)
        for prop in props:
            bboxs.append((
                lab,
                (prop.bbox[1], prop.bbox[0], prop.bbox[3], prop.bbox[2])))
    return bboxs


def bbox_tensor_to_bbox(bboxs_tensor):
    bboxs = []
    for bbox_tensor in bboxs_tensor:
        if bbox_tensor[0] == -1:
            break

        bbox = (bbox_tensor[0].item(), (bbox_tensor[1].item(),
                                        bbox_tensor[2].item(),
                                        bbox_tensor[3].item(),
                                        bbox_tensor[4].item()))
        bboxs.append(bbox)
    return bboxs


def resize_my_images(src, dst, is_masks, bboxs_src=None, bboxs_dst=None):
    '''
    credits: https://evigio.com/post/resizing-images-into-squares-with-opencv-and-python
    '''
    resize_bboxs = bboxs_src is not None

    i = 1
    img_size = 224
    path = src
    for img_name in sorted(os.listdir(path)):
        img = None
        print(img_name)

        if resize_bboxs:
            bboxs_name = img_name[:-4] + '.txt'
            bboxs = load_bboxs(os.path.join(bboxs_src, bboxs_name))

        if not is_masks:
            img = cv2.imread(os.path.join(path, img_name))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        elif is_masks:
            img = cv2.imread(os.path.join(path, img_name),
                             cv2.IMREAD_GRAYSCALE)

        h, w = img.shape[:2]
        a1 = w/h
        a2 = h/w

        if(a1 > a2):
            # if width greater than height
            w_target = round(img_size * a1)
            h_target = img_size

            r_img = cv2.resize(
                img, (w_target, h_target), interpolation=cv2.INTER_AREA)
            margin = int(r_img.shape[1] / 6)
            crop_img = r_img[0:img_size, margin:(margin+img_size)]

            if resize_bboxs:
                # MODIFY BBOX
                for bbox_id, bbox in enumerate(bboxs):
                    label, (xmin, ymin, xmax, ymax) = bbox

                    newxmin = int(xmin * (w_target / w))  # + margin
                    newymin = int(ymin * (h_target / h))
                    newxmax = int(xmax * (w_target / w))  # + margin
                    newymax = int(ymax * (h_target / h))

                    bboxs[bbox_id] = (
                        label, (newxmin, newymin, newxmax, newymax))

        elif(a1 < a2):
            # if height greater than width
            w_target = img_size
            h_target = round(img_size * a2)

            r_img = cv2.resize(img, (w_target, h_target),
                               interpolation=cv2.INTER_AREA)
            margin = int(r_img.shape[0] / 6)
            crop_img = r_img[margin:(margin+img_size), 0:img_size]

            if resize_bboxs:
                # MODIFY BBOX
                for bbox_id, bbox in enumerate(bboxs):
                    label, (xmin, ymin, xmax, ymax) = bbox

                    newxmin = int(xmin * (w_target / w))
                    newymin = int(ymin * (h_target / h))  # + margin
                    newxmax = int(xmax * (w_target / w))
                    newymax = int(ymax * (h_target / h))  # + margin

                    bboxs[bbox_id] = (
                        label, (newxmin, newymin, newxmax, newymax))

        elif(a1 == a2):
            # if height and width are equal
            w_target = img_size
            h_target = img_size

            r_img = cv2.resize(img, (w_target, h_target),
                               interpolation=cv2.INTER_AREA)
            crop_img = r_img[0:img_size, 0:img_size]

            if resize_bboxs:
                # MODIFY BBOX
                for bbox_id, bbox in enumerate(bboxs):
                    label, (xmin, ymin, xmax, ymax) = bbox

                    newxmin = int(xmin * (w_target / w))
                    newymin = int(ymin * (h_target / h))
                    newxmax = int(xmax * (w_target / w))
                    newymax = int(ymax * (h_target / h))

                    bboxs[bbox_id] = (
                        label, (newxmin, newymin, newxmax, newymax))

        if(crop_img.shape[0] != img_size or crop_img.shape[1] != img_size):
            # print('someting....')
            crop_img = r_img[0:img_size, 0:img_size]

        if(crop_img.shape[0] == img_size and crop_img.shape[1] == img_size):

            if not is_masks:
                # SAVING AS RGB FORMAT
                cv2.imwrite(dst + img_name, crop_img[:, :, ::-1])
            elif is_masks:
                cv2.imwrite(dst + img_name, crop_img)

            # SAVE BBOXS
            if resize_bboxs:
                save_bboxs(bboxs_dst + bboxs_name, bboxs)

            i += 1


def display_image(img):
    '''
    using cv2.imshow("image", img)
    cv2.waitKey(); 
    crashes notebooks

    '''
    from matplotlib import pyplot as plt
    plt.imshow(img,)
    plt.show()


if __name__ == '__main__':
    bboxs = load_bboxs(
        './EDD2020_release-I_2020-01-15/bbox/EDD2020_ACB0001.txt')
    print(bboxs)

    save_bboxs('./EDD2020_release-I_2020-01-15/test_bbox.txt', bboxs)

    bboxs = load_bboxs(
        './EDD2020_release-I_2020-01-15/test_bbox.txt')
    print(bboxs)
