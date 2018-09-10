import enum


class Enum(enum.Enum):
    @classmethod
    def choices(cls):
        return cls.CHOICES.value

    @property
    def label(self):
        return ' '.join(map(lambda x: x.capitalize(), self.name.split('_')))
