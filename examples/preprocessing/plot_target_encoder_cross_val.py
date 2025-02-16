"""
==========================================
Target Encoder's Internal Cross Validation
==========================================

.. currentmodule:: sklearn.preprocessing

The :class:`TargetEnocoder` replaces each category of a categorical feature with
the mean of the target variable for that category. This method is useful
in cases where there is a strong relationship between the categorical feature
and the target. To prevent overfitting, :meth:`TargetEncoder.fit_transform` uses
interval cross validation to encode the training data to be used by a downstream
model. In this example, we demonstrate the importance of the cross validation
procedure to prevent overfitting.
"""

# %%
# Create Synthetic Dataset
# ========================
# For this example, we build a dataset with three categorical features: an informative
# feature with medium cardinality, an uninformative feature with medium cardinality,
# and an uninformative feature with high cardinality. First, we generate the informative
# feature:
import numpy as np

from sklearn.preprocessing import KBinsDiscretizer

n_samples = 50_000

rng = np.random.RandomState(42)
y = rng.randn(n_samples)
noise = 0.5 * rng.randn(n_samples)
n_categories = 100

kbins = KBinsDiscretizer(
    n_bins=n_categories, encode="ordinal", strategy="uniform", random_state=rng
)
X_informative = kbins.fit_transform((y + noise).reshape(-1, 1))

# Remove the linear relationship between y and the bin index by permuting the values of
# X_informative
permuted_categories = rng.permutation(n_categories)
X_informative = permuted_categories[X_informative.astype(np.int32)]

# %%
# The uninformative feature with medium cardinality is generated by permuting the
# informative feature and removing the relationship with the target:
X_shuffled = rng.permutation(X_informative)

# %%
# The uninformative feature with high cardinality is generated so that is independent of
# the target variable. We will show that target encoding without cross validation will
# cause catastrophic overfitting for the downstream regressor. These high cardinality
# features are basically unique identifiers for samples which should generally be
# removed from machine learning dataset. In this example, we generate them to show how
# :class:`TargetEncoder`'s default cross validation behavior mitigates the overfitting
# issue automatically.
X_near_unique_categories = rng.choice(
    int(0.9 * n_samples), size=n_samples, replace=True
).reshape(-1, 1)

# %%
# Finally, we assemble the dataset and perform a train test split:
import pandas as pd

from sklearn.model_selection import train_test_split

X = pd.DataFrame(
    np.concatenate(
        [X_informative, X_shuffled, X_near_unique_categories],
        axis=1,
    ),
    columns=["informative", "shuffled", "near_unique"],
)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)

# %%
# Training a Ridge Regressor
# ==========================
# In this section, we train a ridge regressor on the dataset with and without
# encoding and explore the influence of target encoder with and without the
# interval cross validation. First, we see the Ridge model trained on the
# raw features will have low performance, because the order of the informative
# feature is not informative:
import sklearn
from sklearn.linear_model import Ridge

# Configure transformers to always output DataFrames
sklearn.set_config(transform_output="pandas")

ridge = Ridge(alpha=1e-6, solver="lsqr", fit_intercept=False)

raw_model = ridge.fit(X_train, y_train)
print("Raw Model score on training set: ", raw_model.score(X_train, y_train))
print("Raw Model score on test set: ", raw_model.score(X_test, y_test))

# %%
# Next, we create a pipeline with the target encoder and ridge model. The pipeline
# uses :meth:`TargetEncoder.fit_transform` which uses cross validation. We see that
# the model fits the data well and generalizes to the test set:
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import TargetEncoder

model_with_cv = make_pipeline(TargetEncoder(random_state=0), ridge)
model_with_cv.fit(X_train, y_train)
print("Model with CV on training set: ", model_with_cv.score(X_train, y_train))
print("Model with CV on test set: ", model_with_cv.score(X_test, y_test))

# %%
# The coefficients of the linear model shows that most of the weight is on the
# feature at column index 0, which is the informative feature
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["figure.constrained_layout.use"] = True

coefs_cv = pd.Series(
    model_with_cv[-1].coef_, index=model_with_cv[-1].feature_names_in_
).sort_values()
_ = coefs_cv.plot(kind="barh")

# %%
# While :meth:`TargetEncoder.fit_transform` uses an interval cross validation,
# :meth:`TargetEncoder.transform` itself does not perform any cross validation.
# It uses the aggregation of the complete training set to transform the categorical
# features. Thus, we can use :meth:`TargetEncoder.fit` followed by
# :meth:`TargetEncoder.transform` to disable the cross validation. This encoding
# is then passed to the ridge model.
target_encoder = TargetEncoder(random_state=0)
target_encoder.fit(X_train, y_train)
X_train_no_cv_encoding = target_encoder.transform(X_train)
X_test_no_cv_encoding = target_encoder.transform(X_test)

model_no_cv = ridge.fit(X_train_no_cv_encoding, y_train)

# %%
# We evaluate the model on the non-cross validated encoding and see that it overfits:
print(
    "Model without CV on training set: ",
    model_no_cv.score(X_train_no_cv_encoding, y_train),
)
print(
    "Model without CV on test set: ", model_no_cv.score(X_test_no_cv_encoding, y_test)
)

# %%
# The ridge model overfits, because it assigns more weight to the extremely high
# cardinality feature relative to the informative feature.
coefs_no_cv = pd.Series(
    model_no_cv.coef_, index=model_no_cv.feature_names_in_
).sort_values()
_ = coefs_no_cv.plot(kind="barh")

# %%
# Conclusion
# ==========
# This example demonstrates the importance of :class:`TargetEncoder`'s interval cross
# validation. It is important to use :meth:`TargetEncoder.fit_transform` to encode
# training data before passing it to a machine learning model. When a
# :class:`TargetEncoder` is a part of a :class:`~sklearn.pipeline.Pipeline` and the
# pipeline is fitted, the pipeline will correctly call
# :meth:`TargetEncoder.fit_transform` and pass the encoding along.
