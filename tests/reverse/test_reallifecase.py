import io
import PIL
import odin
import requests
import responses

from urllib.parse import urlparse

from odin.codecs import csv_codec
from os import path
from decimal import Decimal as D

from django.core.files import File
from django.test import TestCase

from oscar.core.loading import get_model, get_class

from django.utils.text import slugify

from oscar_odin.fields import DecimalField
from oscar_odin.mappings.catalogue import products_to_db
from oscar_odin.resources.catalogue import (
    Product as ProductResource,
    Image as ImageResource,
    ProductClass as ProductClassResource,
    Category as CategoryResource,
    ProductAttributeValue as ProductAttributeValueResource,
)

Product = get_model("catalogue", "Product")
ProductClass = get_model("catalogue", "ProductClass")
ProductAttribute = get_model("catalogue", "ProductAttribute")
ProductAttributeValue = get_model("catalogue", "ProductAttributeValue")
ProductImage = get_model("catalogue", "ProductImage")
Category = get_model("catalogue", "Category")
Partner = get_model("partner", "Partner")

create_from_breadcrumbs = get_class("catalogue.categories", "create_from_breadcrumbs")


class CSVProductResource(odin.Resource):
    id = odin.IntegerField()
    name = odin.StringField()
    category_id = odin.IntegerField()
    weight = odin.IntegerField()
    weight_type = odin.StringField()
    price = DecimalField()
    image = odin.StringField(null=True)
    app_image = odin.StringField(null=True)
    description = odin.StringField(null=True)
    ean = odin.StringField(null=True)
    number = odin.StringField(null=True)
    supplier_id = odin.IntegerField()
    active = odin.BooleanField()
    unit = odin.StringField()
    tags = odin.StringField(null=True)
    storage_type = odin.StringField()
    assortmentclass = odin.StringField()


class CSVProductMapping(odin.Mapping):
    from_obj = CSVProductResource
    to_obj = ProductResource

    mappings = (
        odin.define(from_field="number", to_field="upc"),
        odin.define(from_field="name", to_field="title"),
        odin.define(from_field="active", to_field="is_public"),
    )

    @odin.map_list_field(from_field="category_id")
    def categories(self, category_id):
        return [CategoryResource(code=category_id)]

    @odin.map_field(from_field="name")
    def slug(self, name):
        return slugify(name)

    @odin.map_field(
        from_field=["weight", "weight_type", "ean", "unit", "tags", "storage_type"]
    )
    def attributes(self, weight, weight_type, ean, unit, tags, storage_type):
        return {
            "weight": weight,
            "weight_type": weight_type,
            "ean": ean,
            "unit": unit,
            "tags": tags,
            "storage_type": storage_type,
        }

    @odin.map_list_field(from_field=["image", "app_image"])
    def images(self, image, app_image):
        images = []

        if image:
            response = requests.get(image)
            a = urlparse(image)
            img = File(io.BytesIO(response.content), name=path.basename(a.path))
            images.append(
                ImageResource(
                    display_order=0,
                    code="%s?upc=%s" % (self.source.number, image),
                    caption="",
                    original=img,
                )
            )

        if app_image and app_image != image:
            response = requests.get(app_image)
            a = urlparse(app_image)
            img = File(io.BytesIO(response.content), name=path.basename(a.path))
            images.append(
                ImageResource(
                    display_order=1,
                    caption="",
                    code="%s?upc=%s-2" % (self.source.number, image),
                    original=img,
                )
            )

        return images

    @odin.map_field(from_field="supplier_id")
    def partner(self, supplier_id):
        partner, _ = Partner.objects.get_or_create(name=supplier_id)
        return partner

    @odin.assign_field
    def product_class(self):
        return ProductClassResource(slug="standard")

    @odin.assign_field
    def structure(self):
        return Product.STANDALONE

    @odin.assign_field
    def is_discountable(self):
        return True




class AutomagicProductResource(odin.Resource):
    SKU = odin.StringField()
    TITLE = odin.StringField(null=True)
    CATEGORY_IDS = odin.StringField(null=True)
    PRICE = odin.StringField(null=True)
    SPECIAL_PRICE = odin.StringField(null=True)
    IMAGE_URL = odin.StringField()
    UNITS = odin.StringField(null=True)
    UNIT_SCALE = odin.StringField(null=True)
    UNIT_SIZE = odin.StringField(null=True)
    UNITS_PER_CASE = odin.StringField(null=True)
    STOCK = odin.StringField()
    MAX_QTY = odin.StringField()
    MIN_QTY = odin.StringField(null=True)
    SHORT_DESCRIPTION = odin.StringField(null=True)
    DESCRIPTION = odin.StringField(null=True)
    BRAND = odin.StringField(null=True)
    BARCODES = odin.StringField()
    PROMOTED = odin.StringField()
    BADGE_ONE = odin.StringField(null=True)
    KEYWORDS = odin.StringField(null=True)


class MyProductResource(ProductResource):
    long_description = odin.StringField(null=True)

    class Meta:
        namespace = "oscar.catalogue"

class AutomagicProductMapping(odin.Mapping):
    from_obj = AutomagicProductResource
    to_obj = MyProductResource

    mappings = (
        odin.define(from_field="SKU", to_field="upc"),
        odin.define(from_field="SHORT_DESCRIPTION", to_field="description"),
        # odin.define(from_field="DESCRIPTION", to_field="long_description"),
    )

    @odin.map_field(from_field=["SKU", "TITLE"])
    def title(self, upc, title):
        return title if title else upc

    @odin.map_field(from_field=["SKU", "TITLE"])
    def slug(self, upc, title):
        return slugify(title) if title else slugify(upc)

    @odin.assign_field
    def product_class(self):
        return ProductClassResource(slug="default")

    @odin.assign_field(to_field="structure")
    def structure(self):
        return "standalone"

    @odin.map_field(
        from_field=[
            "UNITS", "UNIT_SCALE", "UNIT_SIZE", "UNITS_PER_CASE", "MAX_QTY", "MIN_QTY",
            "BRAND", "BARCODES", "PROMOTED", "BADGE_ONE", "KEYWORDS",
        ]
    )
    def attributes(
        self, units, unit_scale, unit_size, units_per_case, max_qty,
        min_qty, brand, barcodes, promoted, badge_one, keywords
    ):
        return {
            "stock_id": "",
            "units": units,
            "unit_scale": unit_scale,
            "unit_size": unit_size,
            "units_per_case": units_per_case,
            "max_qty": int(D(max_qty)) if max_qty else None,
            "min_qty": int(D(min_qty)) if min_qty else None,
            "brand": brand,
            "barcodes": barcodes,
            "promoted": False if promoted == "0" else True,
            "badge_one": badge_one,
            "keywords": keywords
        }

AUTOMAGIC_ATTRIBUTES = {
    "stock_id": ProductAttribute.TEXT,
    "units": ProductAttribute.TEXT,
    "unit_scale": ProductAttribute.TEXT,
    "unit_size": ProductAttribute.TEXT,
    "units_per_case": ProductAttribute.TEXT,
    "max_qty": ProductAttribute.INTEGER,
    "min_qty": ProductAttribute.INTEGER,
    "brand": ProductAttribute.TEXT,
    "barcodes": ProductAttribute.TEXT,
    "promoted": ProductAttribute.BOOLEAN,
    "badge_one": ProductAttribute.TEXT,
    "keywords": ProductAttribute.TEXT,
}

class RealLifeTest(TestCase):
    @responses.activate
    def test_mapping(self):
        product_class, _ = ProductClass.objects.get_or_create(
            name="Default", track_stock=True
        )
        for attr_code, attr_type in AUTOMAGIC_ATTRIBUTES.items():
            product_class.attributes.get_or_create(
                code=attr_code,
                defaults={"name": attr_code.capitalize(), "type": attr_type},
            )

        products = None
        with open("products.csv", "r", encoding="utf-8") as file_obj:
            automagic_product_resources = csv_codec.reader(
                file_obj,
                AutomagicProductResource,
                includes_header=True,
            )
            product_resources = AutomagicProductMapping.apply(
                automagic_product_resources
            )
            products, _ = products_to_db(product_resources)
        print(products)
        return
        responses.add(
            responses.GET,
            "https://picsum.photos/200/300",
            body="Dit is nep content van een image",
            status=200,
            content_type="image/jpeg",
        )

        for partner_id in ["1049", "1052", "1053", "1049"]:
            Partner.objects.get_or_create(
                code=partner_id, defaults={"name": partner_id}
            )

        # Create product class
        product_class, _ = ProductClass.objects.get_or_create(
            slug="standard",
            defaults={
                "name": "Standard product class",
                "requires_shipping": True,
                "track_stock": False,
            },
        )
        ProductAttribute.objects.get_or_create(
            code="weight",
            product_class=product_class,
            defaults={"name": "Weight", "type": ProductAttribute.INTEGER},
        )
        ProductAttribute.objects.get_or_create(
            code="weight_type",
            product_class=product_class,
            defaults={"name": "Weight type", "type": ProductAttribute.TEXT},
        )
        ProductAttribute.objects.get_or_create(
            code="ean",
            product_class=product_class,
            defaults={"name": "EAN", "type": ProductAttribute.TEXT},
        )
        ProductAttribute.objects.get_or_create(
            code="unit",
            product_class=product_class,
            defaults={"name": "Unit", "type": ProductAttribute.TEXT},
        )
        ProductAttribute.objects.get_or_create(
            code="tags",
            product_class=product_class,
            defaults={"name": "Tags", "type": ProductAttribute.TEXT},
        )
        ProductAttribute.objects.get_or_create(
            code="storage_type",
            product_class=product_class,
            defaults={"name": "Storage type", "type": ProductAttribute.TEXT},
        )

        # Create all the categories at first and assign a unique code
        for cat_id in ["101", "213", "264"]:
            cat = create_from_breadcrumbs(cat_id)
            cat.code = cat_id
            cat.save()

        # Get csv file and open it
        csv_file = self.get_csv_fixture("products.csv")
        with open(csv_file) as f:
            # Use odin codec to load in csv to our created resource
            products = csv_codec.reader(f, CSVProductResource, includes_header=True)

            # Map the csv resources to product resources
            product_resources = CSVProductMapping.apply(products)

            # Map the product resources to products and save in DB
            products_to_db(product_resources)

            self.assertEqual(Product.objects.all().count(), 59)
            self.assertEqual(ProductAttributeValue.objects.all().count(), 257)
            self.assertEqual(ProductImage.objects.all().count(), 52)

    def get_csv_fixture(self, filename):
        return path.realpath(
            path.join(
                path.dirname(__file__),
                "../../",
                "oscar_odin/fixtures/oscar_odin/csv/",
                filename,
            )
        )
