# Oscar Odin

Mapping of Oscar eCommerce models to Odin resources.

## Installation

To install add `oscar_odin` to your installed apps

## Usage

```python
from oscar.core.loading import get_model
from oscar_odin.mappings import catalogue

Product = get_model("catalogue", "Product")

# Map a product to a resource.
product = Product.objects.get(id=1)
product_resource = catalogue.product_to_resource(product)
```

# run tests

make install
make tests