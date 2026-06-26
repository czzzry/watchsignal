# Portfolio Notes

This project can become a strong public artifact if it emphasizes product judgment and governance rather than personal household data.

## Good public artifacts

- Decision register showing option space and tradeoffs
- ADRs after founder approval
- Sanitized workflow maps and architecture diagrams
- Synthetic datasets and fake examples
- Notes on how AI assistance was governed rather than trusted blindly

## Bad public artifacts

- Real household messages
- Real names or Telegram identifiers
- Real credentials or credential screenshots
- Workflow exports that embed private headers, tokens, or payload traces

## Public story to aim for

The strongest story is not "I built a movie bot."
The stronger story is "I scoped a decision-heavy product, kept architecture reversible, and governed AI-assisted implementation with explicit artifacts."

## Release rule

Do not publish technical artifacts until they have been checked for:

- private values
- personal identifiers
- real screenshots
- embedded secrets
- accidental household context
