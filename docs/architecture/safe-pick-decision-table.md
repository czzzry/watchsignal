# Safe Pick Decision Table

This table records the first code-backed Safe Pick policy.
It is intentionally conservative because TMDb provider data cannot prove every provider-specific audio or subtitle track.

| Candidate evidence | Classification | Reason |
|---|---|---|
| Prime Video Germany appears in the flatrate bucket and English audio is verified by original or spoken-language metadata | Safe Pick | Subscription availability and language compatibility are both verified enough for MVP use. |
| Prime Video Germany appears in the flatrate bucket and English subtitles are verified | Safe Pick | Foreign-language viewing is acceptable when English subtitles are verified. |
| Prime Video Germany appears only as rent or buy, or Amazon Video appears only as rent or buy | Needs Quick Check | Paid rental or purchase does not count as Prime subscription availability. |
| Prime Video Germany appears in the flatrate bucket, but the title has no verified English audio or English subtitles | Needs Quick Check | TMDb does not prove provider-specific English audio or subtitle availability. |
| Bucketed provider data is missing, but a legacy provider name is present | Needs Quick Check | The app should not treat unbucketed provider names as subscription availability. |
| The title is already watched and rewatches are not explicitly allowed | Rejected | Rewatch avoidance remains a hard default. |
| A manual correction says the title is verified watchable and no hard rejection applies | Safe Pick | Manual verification can upgrade uncertain provider or subtitle data. |
| A manual correction says the title is not watchable | Rejected | Manual correction can also clarify that a candidate should not be recommended. |
