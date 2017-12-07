#!/usr/bin/env python
import rospkg

import cv2
import gc
import numpy as np
import pandas as pd

from imblearn.under_sampling import RandomUnderSampler

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

rospack = rospkg.RosPack()
pkg_path = rospack.get_path('stopsign')

IMAGE_RATE = 11 # hz

BULK_DATA_FILE = '%s/data/003_manual_labels/all.csv' % (pkg_path,)

start_image_id = 0
end_image_id = 2189

IMAGE_BASE_STRING = '%s/data/002_original_images/%s' % (pkg_path, 'frame%04d.jpg')

NUM_IMAGES = end_image_id - start_image_id
NUM_ORBS_FEATURES = 500

descriptors = []
for i in range(32):
    descriptors.append('descr%02d' % (i,))

klass = ['class'.ljust(7), 'imageid']

def get_image(image_id):
    filename = IMAGE_BASE_STRING % (image_id,)
    return cv2.imread(filename, cv2.IMREAD_COLOR)

def load_data(seed=None):
    df = pd.read_csv(BULK_DATA_FILE, header=0)
    # mutate data back from stored form
    df['class  '] = df['class  '].apply(lambda cls: cls / 1000.0)
    df['angle  '] = df['angle  '].apply(lambda ang: ang / 1000.0)
    df['respons'] = df['respons'].apply(lambda res: res / 100000000.0)

    # split into class, features
    X = df[descriptors]
    y = df[klass]
    print(y.describe())

    # use mask to split into test, train
    if seed is not None:
        np.random.seed(seed)
    img_msk = np.random.rand(NUM_IMAGES) < 0.8
    X['train'] = y['imageid'].apply(lambda x: img_msk[x])
    X_msk = X['train'] == 1
    y['train'] = y['imageid'].apply(lambda x: img_msk[x])
    y_msk = y['train'] == 1
    train_X = X[X_msk].as_matrix()
    test_X = X[~X_msk].as_matrix()
    train_y = y['class  '][y_msk].as_matrix().ravel()
    test_y = y['class  '][~y_msk].as_matrix().ravel()
    train_id = y['imageid'][y_msk].as_matrix().ravel()
    test_id = y['imageid'][~y_msk].as_matrix().ravel()
    return train_X, train_y, train_id, test_X, test_y, test_id

def load_data_by_image(start_id, end_id, seed=12345):
    # lazy load image data?
    df = pd.read_csv(BULK_DATA_FILE, header=0, skiprows=lambda x: 1 <= x <= start_id*500, nrows=500*(end_id - start_id))
    print(df.describe())
    import sys
    sys.exit(1)
    # split into class, features
    X = df[descriptors]
    y = df[klass]
    print(y.describe())

    # use mask to split into test, train
    if seed is not None:
        np.random.seed(seed)
    img_msk = np.random.rand(NUM_IMAGES) < 0.8
    X['train'] = y['imageid'].apply(lambda x: img_msk[x])
    X_msk = X['train'] == 1
    y['train'] = y['imageid'].apply(lambda x: img_msk[x])
    y_msk = y['train'] == 1
    train_X = X[X_msk].as_matrix()
    test_X = X[~X_msk].as_matrix()
    train_y = y['class  '][y_msk].as_matrix().ravel()
    test_y = y['class  '][~y_msk].as_matrix().ravel()
    train_id = y['imageid'][y_msk].as_matrix().ravel()
    test_id = y['imageid'][~y_msk].as_matrix().ravel()
    return train_X, train_y, train_id, test_X, test_y, test_id

def subsample_data(X, y, ratio=0.5, seed=None):
    size = 1100
    rus = RandomUnderSampler(
        ratio={
            0: int(size * ratio),
            1: int(size * (1 - ratio)),
        },
        random_state=seed)
    return rus.fit_sample(X, y)

if __name__ == '__main__':
    ### Begin the whole process ###

    '''
    Things to work on:
    Vary up the dataset:
        - Classify the total image instead of just one keypoint
            - Learn based on the classification of all of the keypoints in the 
            image and their location
    '''

    # load data from csv, split into training and test sets
    print('begin loading data')
    train_X, train_y, train_id, test_X, test_y, test_id = load_data_by_image(0, 10)
    import sys
    sys.exit(1)

    print('train kp classifier')
    kp_nbrs = KNeighborsClassifier()
    # train_X, train_y = subsample_data(train_X, train_y, ratio=0.5, seed=123456)
    kp_nbrs.fit(train_X, train_y)

    # I need to group by images first
    gc.collect()
    image_train_X = np.zeros((len(train_X), NUM_ORBS_FEATURES,))
    image_train_y = np.zeros((len(train_y), 1)).ravel()
    image_test_X = np.zeros((len(test_X), NUM_ORBS_FEATURES,))
    image_test_y = np.zeros((len(test_y), 1)).ravel()

    itr = 0
    ite = 0

    print('groupby image')
    # compile images into features (classification of keypoints)
    #   and the actual label for the image
    for i in range(start_image_id, end_image_id):
        mask = train_id == i
        subset_X = train_X[mask]
        if len(subset_X) > 0:
            subset_y = train_y[mask]

            predict_y = kp_nbrs.predict(subset_X).flatten()
            image_train_X[itr, :] = predict_y
            image_train_y[itr] = (train_y == 1).any()
            itr += 1

        subset_X = test_X[mask]
        if len(subset_X) > 0:
            subset_y = test_y[mask]

            image_test_X[ite, :] = subset_y
            image_test_y[ite] = (subset_y == 1).any()
            ite += 1


    print('train image classifier on groupby image')
    gnb = GaussianNB()
    gnb.fit(image_train_X, image_train_y)

    image_y_pred = gnb.predict(image_test_X)

    print('ready to predictt on test data')
    print(gnb)
    print('a: %.4f (percent correctly classified)' % (accuracy_score(y_true=image_test_y, y_pred=image_y_pred),))
    print('p: %.4f (percent of correct positives)' % (precision_score(y_true=image_test_y, y_pred=image_y_pred),))
    print('r: %.4f (percent of positive results found)' % (recall_score(y_true=image_test_y, y_pred=image_y_pred),))
    print('---')