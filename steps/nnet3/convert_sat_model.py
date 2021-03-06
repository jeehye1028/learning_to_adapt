import os
import sys

import numpy as np
import keras
import kaldi_io
import tensorflow as tf

from keras.models import Model
from keras.layers import Input
from learning_to_adapt.model import load_model, LHUC, SparseLHUC, SDBatchNormalization, UttBatchNormalization


if __name__ == '__main__':
    model_in = sys.argv[1]
    model_out = sys.argv[2]

    if not model_in.endswith('.h5') or not model_out.endswith('.h5'):
        raise TypeError ('Unsupported model type. Please use h5 format. Update Keras if needed')

    feats = np.random.normal(size=(1, 33, 40))
    spks = np.zeros((1, 1))

    m_in = load_model(model_in)
    y_in = m_in.predict([feats, spks])

    x = y = Input(shape=(None, 40))
    for l in m_in.layers:
        if l.name.startswith('input') or l.name.startswith('multiply') or l.name.startswith('sparse_multiply'):
            continue

        if l.name.startswith('lhuc'):
            y = LHUC(name=l.name, weights=[l.get_weights()[0][0]])(y)
        elif l.name.startswith('sparse_lhuc'):
            regularizer = l.activity_regularizer
            beta = regularizer.beta
            gamma = regularizer.gamma
            delta = regularizer.delta

            y = SparseLHUC(beta, gamma, delta, regularizer, name=l.name, weights=[l.get_weights()[0][0]])(y)
        elif l.name.endswith('batchnorm') and isinstance(l, SDBatchNormalization):
            weights = l.get_weights()
            gamma = weights[0][0]
            beta = weights[1][0]

            y = UttBatchNormalization(name='lhuc.%s' % l.name, weights=[gamma, beta])(y)
        else:
            y = l(y)

    m_out = Model(inputs=x, outputs=y)
    m_out.compile(loss='sparse_categorical_crossentropy', optimizer='sgd')
    m_out.save(model_out)
    m_out.summary()
    del m_out

    m_out = load_model(model_out)
    y_out = m_out.predict(feats)
    assert np.allclose(y_in, y_out)
