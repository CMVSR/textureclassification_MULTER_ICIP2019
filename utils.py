import os
from PIL import Image

import torch
import torch.utils.data as data
from torchvision.transforms import *


class MINCDataset(data.Dataset):
    NUM_CLASS = 23

    def __init__(self, root=os.path.expanduser('/home/zhen/WorkSpace/data/minc-2500'),
                 split='train', transform=None):
        self.transform = transform
        classes, class_to_idx = find_classes(root + '/images')
        if split == 'train':
            filename = os.path.join(root, 'labels/train1.txt')
        else:
            filename = os.path.join(root, 'labels/test1.txt')

        self.images, self.labels = make_dataset(filename, root, class_to_idx)
        assert (len(self.images) == len(self.labels))

    def __getitem__(self, index):
        _img = Image.open(self.images[index]).convert('RGB')
        _label = self.labels[index]
        if self.transform is not None:
            _img = self.transform(_img)

        return _img, _label

    def __len__(self):
        return len(self.images)


def find_classes(dir):
    classes = [d for d in os.listdir(dir) if os.path.isdir(os.path.join(dir, d))]
    classes.sort()
    class_to_idx = {classes[i]: i for i in range(len(classes))}
    return classes, class_to_idx


def make_dataset(filename, datadir, class_to_idx):
    images = []
    labels = []
    with open(os.path.join(filename), "r") as lines:
        for line in lines:
            _image = os.path.join(datadir, line.rstrip('\n'))
            _dirname = os.path.split(os.path.dirname(_image))[1]
            assert os.path.isfile(_image)
            label = class_to_idx[_dirname]
            images.append(_image)
            labels.append(label)

    return images, labels


def get_transform(dataset, large_test_crop=False):
    normalize = Normalize(mean=[0.485, 0.456, 0.406],
                          std=[0.229, 0.224, 0.225])
    if dataset == 'imagenet':
        transform_train = Compose([
            Resize(256),
            RandomResizedCrop(224),
            RandomHorizontalFlip(),
            ColorJitter(0.4, 0.4, 0.4),
            ToTensor(),
            Lighting(0.1, _imagenet_pca['eigval'], _imagenet_pca['eigvec']),
            normalize,
        ])
        if large_test_crop:
            transform_val = Compose([
                Resize(366),
                CenterCrop(320),
                ToTensor(),
                normalize,
            ])
        else:
            transform_val = Compose([
                Resize(256),
                CenterCrop(224),
                ToTensor(),
                normalize,
            ])
    elif dataset == 'minc':
        transform_train = Compose([
            Resize(256),
            RandomResizedCrop(224),
            RandomHorizontalFlip(),
            ColorJitter(0.4, 0.4, 0.4),
            ToTensor(),
            Lighting(0.1, _imagenet_pca['eigval'], _imagenet_pca['eigvec']),
            normalize,
        ])
        transform_val = Compose([
            Resize(256),
            CenterCrop(224),
            ToTensor(),
            normalize,
        ])
    elif dataset == 'cifar10':
        transform_train = transforms.Compose([
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465),
                                 (0.2023, 0.1994, 0.2010)),
        ])
        transform_val = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465),
                    (0.2023, 0.1994, 0.2010)),
        ])
    return transform_train, transform_val


_imagenet_pca = {
    'eigval': torch.Tensor([0.2175, 0.0188, 0.0045]),
    'eigvec': torch.Tensor([
        [-0.5675,  0.7192,  0.4009],
        [-0.5808, -0.0045, -0.8140],
        [-0.5836, -0.6948,  0.4203],
    ])
}


class Lighting(object):
    """Lighting noise(AlexNet - style PCA - based noise)"""

    def __init__(self, alphastd, eigval, eigvec):
        self.alphastd = alphastd
        self.eigval = eigval
        self.eigvec = eigvec

    def __call__(self, img):
        if self.alphastd == 0:
            return img

        alpha = img.new().resize_(3).normal_(0, self.alphastd)
        rgb = self.eigvec.type_as(img).clone()\
            .mul(alpha.view(1, 3).expand(3, 3))\
            .mul(self.eigval.view(1, 3).expand(3, 3))\
            .sum(1).squeeze()

        return img.add(rgb.view(3, 1, 1).expand_as(img))
