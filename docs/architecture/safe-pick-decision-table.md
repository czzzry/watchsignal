# Safe Pick Decision Table

This table records the first code-backed Safe Pick policy.
It is intentionally conservative because TMDb provider data cannot prove every provider-specific audio or subtitle track.

| Candidate evidence | Classification | Reason |
|---|---|---|
| Prime Video Germany or Amazon Video appears in the flatrate, rent, or buy bucket and English audio is verified by original or spoken-language metadata | Safe Pick | Amazon DE access and language compatibility are both verified enough for MVP use. |
| Prime Video Germany or Amazon Video appears in the flatrate, rent, or buy bucket and English subtitles are verified | Safe Pick | Foreign-language viewing is acceptable when English subtitles are verified. |
| Prime Video Germany or Amazon Video appears in a valid bucket, but the title has no verified English audio or English subtitles | Needs Quick Check | TMDb does not prove provider-specific audio or subtitle availability strongly enough for the main recommendation. |
| Bucketed Amazon DE provider data is missing, but a legacy provider name is present | Needs Quick Check | The app should not treat unbucketed provider names as verified Amazon DE access. |
| The title is already watched and rewatches are not explicitly allowed | Rejected | Rewatch avoidance remains a hard default. |
| A manual correction says the title is verified watchable and no hard rejection applies | Safe Pick | Manual verification can upgrade uncertain provider or subtitle data. |
| A manual correction says the title is not watchable | Rejected | Manual correction can also clarify that a candidate should not be recommended. |
