#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''Tests for model layers'''

import numpy as np
import scipy
import scipy.stats
import tensorflow as tf
from decorator import decorator
from nose.tools import eq_

import crema

@decorator
def new_graph(f, *args, **kwargs):
    tf.set_random_seed(1234)
    np.random.seed(1234)
    g = tf.Graph()
    with g.as_default():
        return f(*args, **kwargs)


def test_dense():

    @new_graph
    def __test(n_filters, nl, reg):
        # Our input batch
        x = np.random.randn(20, 64)

        x_in = tf.placeholder(tf.float32, shape=x.shape, name='x')

        output = crema.model.layers.dense_layer(x_in, n_filters,
                                                nonlinearity=nl,
                                                reg=reg)

        with tf.Session() as sess:
            sess.run(tf.initialize_all_variables())
            y = sess.run(output, feed_dict={x_in: x})

        target_shape = [x.shape[0], n_filters]

        eq_(y.shape, tuple(target_shape))

        if reg:
            eq_(len(tf.get_collection('penalty')), 1)
        else:
            eq_(len(tf.get_collection('penalty')), 0)


    # And a couple of squeeze tests
    for n_filters in [1, 2, 3]:
        for nl in [tf.nn.relu, tf.nn.relu6, None]:
            for reg in [False, True]:
                yield __test, n_filters, nl, reg


def test_conv2_layer():

    @new_graph
    def __test(shape, n_filters, nl, strides, mode, squeeze, reg):
        # Our input batch
        x = np.random.randn(20, 5, 5, 7)

        x_in = tf.placeholder(tf.float32, shape=x.shape, name='x')

        output = crema.model.layers.conv2_layer(x_in, shape, n_filters,
                                                nonlinearity=nl,
                                                strides=strides,
                                                mode=mode,
                                                squeeze_dims=squeeze,
                                                reg=reg)

        with tf.Session() as sess:
            sess.run(tf.initialize_all_variables())
            y = sess.run(output, feed_dict={x_in: x})

        s1, s2 = x.shape[1:3]

        shape = list(shape)

        for i in [0, 1]:
            if shape[i] is None:
                shape[i] = x.shape[i+1]

        if mode == 'VALID':
            s1 = s1 - shape[0] + 1
            s2 = s2 - shape[1] + 1

        if strides is not None:
            s1 = s1 // strides[0] + (s1 % strides[0])
            s2 = s2 // strides[1] + (s2 % strides[1])

        target_shape = [x.shape[0], s1, s2, n_filters]

        if squeeze is not None:
            target_shape = [target_shape[_] for _ in range(4) if _ not in squeeze]

        eq_(y.shape, tuple(target_shape))

        if reg:
            eq_(len(tf.get_collection('penalty')), 1)
        else:
            eq_(len(tf.get_collection('penalty')), 0)


    # And a couple of squeeze tests
    yield __test, [5, 1], 3, tf.nn.relu, None, 'VALID', [1], False
    yield __test, [1, 5], 3, tf.nn.relu, None, 'VALID', [2], False

    for shape in [[1,3], [3, 3], [5, 1], [1, None], [None, 1]]:
        for n_filters in [1, 2, 3]:
            for nl in [tf.nn.relu, tf.nn.relu6, 'relu', None]:
                for reg in [False, True]:
                    if None not in shape:
                        for strides in [None, [min(min(shape), 2), min(min(shape), 2)]]:
                            for mode in ['SAME', 'VALID']:
                                yield __test, shape, n_filters, nl, strides, mode, None, reg
                    else:
                        strides = None
                        for mode in ['SAME', 'VALID']:
                            yield __test, shape, n_filters, nl, strides, mode, None, reg

@new_graph
def test_conv2_multilabel():

    x = np.random.randn(20, 5, 5, 7)

    x_in = tf.placeholder(tf.float32, shape=x.shape, name='x')

    output = crema.model.layers.conv2_multilabel(x_in, 10)

    with tf.Session() as sess:
        sess.run(tf.initialize_all_variables())
        log_y = sess.run(output, feed_dict={x_in: x})

    y = np.exp(log_y)

    assert np.all(y >= 0) and np.all(y <= 1.0)

@new_graph
def test_conv2_softmax():
    x = np.random.randn(10, 5, 1, 3)

    x_in = tf.placeholder(tf.float32, shape=x.shape, name='x')

    output = crema.model.layers.conv2_softmax(x_in, 8)

    with tf.Session() as sess:
        sess.run(tf.initialize_all_variables())
        log_y = sess.run(output, feed_dict={x_in: x})

    y = np.exp(log_y)

    assert np.all(y >= 0) and np.all(y <= 1.0)
    assert np.allclose(np.sum(y, axis=-1), np.ones(y.shape[:-1]))
