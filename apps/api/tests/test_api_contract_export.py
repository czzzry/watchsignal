import unittest

from movie_night_mediator.api.generate_typescript_contract import (
    render_typescript_contract,
)


class ApiContractExportTest(unittest.TestCase):
    def test_generated_contract_includes_core_setup_and_session_shapes(self) -> None:
        contract = render_typescript_contract()

        self.assertIn("export type SetupStatePayload = {", contract)
        self.assertIn("export type SharedSessionPayload = {", contract)
        self.assertIn(
            'export type SessionMode = "husband_first" | "wife_first" | "compromise";',
            contract,
        )
        self.assertIn("export type RecommendationShortlistItemPayload = {", contract)
        self.assertIn("export type TonightIntentInterpretRequestPayload = {", contract)
        self.assertIn("export type TonightIntentInterpretationPayload = {", contract)


if __name__ == "__main__":
    unittest.main()
