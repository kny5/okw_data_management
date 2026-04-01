#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 07:51:41 2024

@author: kny5
"""

import functools
import logging
import re
import unicodedata
from time import sleep

import numpy as np
import pandas as pd
import requests
from fuzzywuzzy import fuzz
from scipy.spatial import KDTree
from sklearn.cluster import DBSCAN
