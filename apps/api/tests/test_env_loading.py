import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from movie_night_mediator.env import load_repo_env


class RepoEnvLoadingTest(unittest.TestCase):
    def test_load_repo_env_sets_missing_values_without_overwriting_existing_ones(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dotenv_path = Path(directory) / ".env"
            dotenv_path.write_text(
                "\n".join(
                    (
                        "# comment",
                        "TMDB_API_KEY=test-key",
                        "OPENAI_API_KEY=\"quoted-openai-key\"",
                        "EXISTING_VAR=from-file",
                    )
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {"EXISTING_VAR": "keep-me"},
                clear=True,
            ):
                load_repo_env(dotenv_path)

                self.assertEqual(os.environ["TMDB_API_KEY"], "test-key")
                self.assertEqual(os.environ["OPENAI_API_KEY"], "quoted-openai-key")
                self.assertEqual(os.environ["EXISTING_VAR"], "keep-me")


if __name__ == "__main__":
    unittest.main()
