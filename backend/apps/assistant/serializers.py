from rest_framework import serializers


class MessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=2000, trim_whitespace=True)


class ContextSerializer(serializers.Serializer):
    district = serializers.CharField(max_length=80, required=False, allow_blank=True)
    crop = serializers.CharField(max_length=40, required=False, allow_blank=True)
    last_check = serializers.CharField(max_length=160, required=False, allow_blank=True)


class ChatRequestSerializer(serializers.Serializer):
    messages = MessageSerializer(many=True, allow_empty=False)
    language = serializers.ChoiceField(choices=["rw", "en", "fr"], default="rw")
    context = ContextSerializer(required=False)

    def validate_messages(self, value):
        if len(value) > 40:
            raise serializers.ValidationError("Too many messages. Start a new conversation.")
        if value[-1]["role"] != "user":
            raise serializers.ValidationError("The last message must be from the user.")
        return value
