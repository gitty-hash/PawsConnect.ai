# Image credits — PawsConnect `Testing_Images`

All eight images were obtained from **Wikimedia Commons** on **2026-10-04**. For each file the license was read from the Commons file-page metadata (API `extmetadata.LicenseShortName`) *before* the image was saved, and only files marked **CC0 (public-domain dedication)** were kept. CC0 permits reuse without attribution; attribution is given anyway as good practice.

**Modifications:** none, other than the 960-px-wide resized copy that Wikimedia's own thumbnail service produced (to keep the project small). The app reads these local files by relative path (`Testing_Images/<name>`) and never downloads them again.

| # | Filename | Role in testing | Source URL (file page) | Source website | Creator | License / reuse status | Original size (px) | Date accessed |
|---|---|---|---|---|---|---|---|---|
| 1 | `dog_01.jpg` | Clear adult dog (Labrador-type) | <https://commons.wikimedia.org/wiki/File:Portrait_of_a_labrador_retriever.jpg> | commons.wikimedia.org | Dktue | CC0 — <http://creativecommons.org/publicdomain/zero/1.0/deed.en> | 6240×4160 | 2026-10-04 |
| 2 | `dog_02.jpg` | Clear puppy (Corgi-type) | <https://commons.wikimedia.org/wiki/File:Fawn_and_white_Welsh_Corgi_puppy_standing_on_rear_legs_and_sticking_out_the_tongue.jpg> | commons.wikimedia.org | Huoadg5888 (minor edits by a Commons subsidiary account) | CC0 — <http://creativecommons.org/publicdomain/zero/1.0/deed.en> | 3126×4682 | 2026-10-04 |
| 3 | `dog_03.jpg` | Clear small dog (Shetland sheepdog-type) | <https://commons.wikimedia.org/wiki/File:Dog-portrait-1367008135LpJ.jpg> | commons.wikimedia.org | Karen Arnold | CC0 — <http://creativecommons.org/publicdomain/zero/1.0/deed.en> | 584×615 | 2026-10-04 |
| 4 | `cat_01.jpg` | Clear adult cat (Siamese-type) | <https://commons.wikimedia.org/wiki/File:Siamese_cat_HD.jpg> | commons.wikimedia.org | Aquinassixthway | CC0 — <http://creativecommons.org/publicdomain/zero/1.0/deed.en> | 2670×4000 | 2026-10-04 |
| 5 | `cat_02.jpg` | Clear cat (tabby/white, blue eyes) | <https://commons.wikimedia.org/wiki/File:Tabby_cat_with_blue_eyes-3336579.jpg> | commons.wikimedia.org | AdinaVoicu | CC0 — <http://creativecommons.org/publicdomain/zero/1.0/deed.en> | 2877×3456 | 2026-10-04 |
| 6 | `multiple_animals.jpg` | HARD CASE: multiple animals in one frame | <https://commons.wikimedia.org/wiki/File:Sleeping_Puppies_in_Ulaanbaatar.jpg> | commons.wikimedia.org | Martin Vorel | CC0 — <http://creativecommons.org/publicdomain/zero/1.0/deed.en> | 2560×1920 | 2026-10-04 |
| 7 | `hard_case_blurry.jpg` | HARD CASE: blurry photo | <https://commons.wikimedia.org/wiki/File:Blurry_picture_a_cat.jpg> | commons.wikimedia.org | Dentsinhere43 | CC0 — <http://creativecommons.org/publicdomain/zero/1.0/deed.en> | 1600×1200 | 2026-10-04 |
| 8 | `no_animal.jpg` | HARD CASE: no animal in the photo (dog bowl) | <https://commons.wikimedia.org/wiki/File:Green_Spiral_Slow_Feeder_Dog_Bowl.jpg> | commons.wikimedia.org | ELTORO.VET | CC0 — <http://creativecommons.org/publicdomain/zero/1.0/deed.en> | 1300×1300 | 2026-10-04 |

## Notes
- `Testing_Images/hard_case_blurry.jpg` (blurry), `multiple_animals.jpg` (three puppies in one frame) and `no_animal.jpg` (a dog bowl, no animal) are the three required *hard cases* for Part B.
- Breed names in Commons file titles/descriptions are **not** used as ground truth anywhere in the app; the vision model's breed guess is always shown with a confidence label and flagged for human review when uncertain.
- No photo shows an identifiable person's face as its subject; no personal data is included.
