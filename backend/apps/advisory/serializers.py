from rest_framework import serializers


class WeatherQuerySerializer(serializers.Serializer):
    city = serializers.CharField(max_length=80)


class AdvisoryRequestSerializer(serializers.Serializer):
    city = serializers.CharField(max_length=80)
    language = serializers.ChoiceField(choices=["rw", "en", "fr"], default="rw")
