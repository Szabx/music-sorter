# music-sorter
Simple script that grinds through music files, and organizes them

# Requirements:
- Python 3 - https://www.python.org/downloads/
- Chromaprint fpcalc - https://acoustid.org/chromaprint
- AcoustID application api key(registration required) - https://acoustid.org/new-application

## Detailed description
Simple script that uses AcoustID to create fingerprints from music files, sends them to [MusicBrainz](https://musicbrainz.org/) to get the meta data, then moves and renames the files, based on the received data.
It can organize it based on either one of these 3 criteria: artist, album or year.

## Usage
`python parser.py --input_path "{source_absolute_path}" --api_key "{acoustid_application_api_key}" --output_path "{destination_absolute_path}" --contact_email "{musicbrainz_contact_email}" --order_by {artist/album/year} --remove_origin --batch_size {number_of_concurrently_processed_files}`

Extra param details:
`--contact_email`: if anything goes wrong on musicbrainz, it's where they'll contact you

`--order_by`: the criteria the files get organized by

`--remove_origin`: removes source files after organized; skip to keep original files
