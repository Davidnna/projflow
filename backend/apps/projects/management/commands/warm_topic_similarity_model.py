from django.core.management.base import BaseCommand, CommandError

from apps.projects.similarity import get_embedding_model


class Command(BaseCommand):
    help = "Download and initialise the local topic similarity model during deployment."

    def handle(self, *args, **options):
        try:
            model = get_embedding_model()
            list(model.embed(["ProjFlow topic similarity model readiness check"], batch_size=1))
        except Exception as exc:
            raise CommandError(
                "The local topic similarity model could not be prepared."
            ) from exc
        self.stdout.write(self.style.SUCCESS("Topic similarity model is ready."))
