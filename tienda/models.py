from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MinLengthValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre


class Cliente(models.Model):
    nombre = models.CharField(max_length=120)
    email = models.EmailField(blank=True, null=True, unique=True)
    telefono = models.CharField(max_length=30, blank=True)

    #  DNI único con validación
    dni = models.CharField(
        max_length=8,
        unique=True,
        validators=[MinLengthValidator(8)]
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre


class Pelicula(models.Model):
    titulo = models.CharField(max_length=200)
    anio = models.PositiveIntegerField(
        validators=[MinValueValidator(1900)],
        verbose_name="Año"
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="peliculas"
    )
    precio_alquiler = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))]
    )

    #  NUEVOS CAMPOS
    stock = models.IntegerField(default=0)
    slug = models.SlugField(unique=True, blank=True)

    duracion_minutos = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    director = models.CharField(max_length=100)
    pais_origen = models.CharField(max_length=50)

    class Meta:
        ordering = ["titulo", "anio"]
        unique_together = [("titulo", "anio")]

    def __str__(self) -> str:
        return f"{self.titulo} ({self.anio})"

    #  SLUG AUTOMÁTICO
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = "medali-40-" + slugify(self.titulo)
        super().save(*args, **kwargs)


class MetodoPago(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre


class Alquiler(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('anulado', 'Anulado'),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="alquileres"
    )
    pelicula = models.ForeignKey(
        Pelicula,
        on_delete=models.PROTECT,
        related_name="alquileres"
    )

    fecha_alquiler = models.DateField(default=timezone.localdate)
    fecha_devolucion = models.DateField(blank=True, null=True)

    #  reemplazamos pagado booleano por estado
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='pendiente'
    )

    fecha_pago = models.DateTimeField(null=True, blank=True)

    metodo_pago = models.ForeignKey(
        MetodoPago,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    precio = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["-fecha_alquiler", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=['cliente', 'pelicula', 'fecha_alquiler'],
                name='unique_alquiler'
            )
        ]

    def __str__(self) -> str:
        return f"Alquiler: {self.pelicula} - {self.cliente}"

    #  VALIDACIÓN DE FECHAS
    def clean(self):
        if self.fecha_devolucion and self.fecha_devolucion < self.fecha_alquiler:
            raise ValidationError("La fecha de devolución no puede ser menor que la de alquiler")

    #  MARCAR COMO PAGADO
    def marcar_pagado(self, fecha_devolucion=None):
        if fecha_devolucion is None:
            fecha_devolucion = timezone.localdate()

        self.estado = 'pagado'
        self.fecha_devolucion = fecha_devolucion
        self.save()

    def save(self, *args, **kwargs):
        #  evitar alquiler sin stock
        if self.pelicula.stock <= 0:
            raise ValidationError("No hay stock disponible para esta película")

        #  asignar precio automáticamente
        if self.precio is None:
            self.precio = self.pelicula.precio_alquiler

        #   registrar fecha_pago automáticamente
        if self.estado == 'pagado' and not self.fecha_pago:
            self.fecha_pago = timezone.now()

        super().save(*args, **kwargs)