import argparse
from pathlib import Path
from typing import List
import shutil
import concurrent.futures
from enum import Enum
from sound_utils import generate_fingerprint, recognize_song_acoustid, get_musicbrainz_metadata

class OrderBy(Enum):
    ARTIST = "artist"
    ALBUM = "album"
    YEAR = "year"

def process_file(file_path: Path, api_key: str, contact_email: str, output_path: Path, remove_origin: bool) -> dict:
    try:
        fingerprint, duration = generate_fingerprint(file_path)
        if not fingerprint or not duration:
            return None
        
        acoustid_result = recognize_song_acoustid(fingerprint, duration, api_key)
        if acoustid_result and "results" in acoustid_result:
            for result in acoustid_result["results"]:
                if "recordings" in result:
                    for recording in result["recordings"]:
                        recording_id = recording.get("id")
                        if recording_id:
                            return get_musicbrainz_metadata(recording_id, contact_email)
                else:
                    # Move file to the "unsorted" folder
                    unsorted_folder = output_path / "unsorted"
                    unsorted_folder.mkdir(parents=True, exist_ok=True)  # Ensure the folder exists
                    destination_file = unsorted_folder / file_path.name

                    # Copy the file
                    shutil.copy2(file_path, destination_file)
                    print(f"No metadata found. Moved {file_path} to {destination_file}")

                    # Remove the original file if the flag is set
                    if remove_origin:
                        try:
                            file_path.unlink()  # Delete the original file
                            print(f"Deleted original file: {file_path}")
                        except Exception as e:
                            print(f"Error deleting original file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None

def process_files_in_batches(
    files: List[Path],
    batch_size: int,
    output_path: Path,
    order_by: str,
    api_key: str,
    contact_email: str,
    remove_origin: bool
) -> None:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for i in range(0, len(files), batch_size):
            batch = files[i : i + batch_size]
            print(f"Processing batch {i // batch_size + 1} of {len(files) // batch_size + 1} with {len(batch)} files.")
            for file_path_original in batch:
                if not file_path_original.exists() or not file_path_original.is_file():
                    print(f"Skipping invalid file: {file_path_original}")
                    continue
                if file_path_original.suffix.lower() not in [".mp3", ".flac", ".wav", ".ogg"]:
                    print(f"Unsupported file format: {file_path_original}")
                    continue
                file_path_str = str(file_path_original)
                file_path = Path(file_path_str.encode("utf-8").decode())
                metadata = process_file(file_path, api_key, contact_email, output_path, remove_origin)
                if metadata:
                    recording = metadata.get("recording", {})
                    
                    # Extract artist(s)
                    artists = []
                    artist_credits = recording.get("artist-credit", [])
                    for artist_credit in artist_credits:
                        if isinstance(artist_credit, dict) and "artist" in artist_credit:
                            artist = artist_credit.get("artist", {})
                            if isinstance(artist, dict):
                                artist_name = artist.get("name")
                                if artist_name:
                                    artists.append(artist_name)
                    artist_name_str = ", ".join(artists) if artists else "Unknown Artist"
                    artist_folder = escape_folder_name("&".join(artists)) if artists else "Unknown Artist"

                    # Extract song name
                    song_name = recording.get("title", "Unknown Song")

                    # Extract album(s)
                    albums = []
                    release_list = recording.get("release-list", [])
                    for release in release_list:
                        album_title = release.get("title")
                        if album_title:
                            albums.append(album_title)
                    album_folder = escape_folder_name("&".join(albums)) if albums else "Unknown Album"

                    # Extract year(s)
                    years = []
                    for release in release_list:
                        release_date = release.get("date")
                        if release_date:
                            years.append(release_date.split("-")[0])  # Extract only the year part
                    year_folder = escape_folder_name("&".join(years)) if years else "Unknown Year"

                    # Determine folder name based on order_by
                    if order_by == "artist":
                        folder_name = artist_folder
                    elif order_by == "album":
                        folder_name = album_folder
                    elif order_by == "year":
                        folder_name = year_folder
                    else:
                        folder_name = "unsorted"

                    # Create destination folder
                    destination_folder = output_path / folder_name
                    destination_folder.mkdir(parents=True, exist_ok=True)

                    # Rename copied file
                    escaped_file_name = escape_folder_name(f"{artist_name_str} - {song_name}{file_path.suffix}")
                    destination_file = destination_folder / escaped_file_name

                    # Copy the file
                    shutil.copy2(file_path, destination_file)
                    print(f"Copied {file_path} to {destination_file}")

                    # Remove the original file if the flag is set
                    if remove_origin:
                        try:
                            file_path.unlink()  # Delete the original file
                            print(f"Deleted original file: {file_path}")
                        except Exception as e:
                            print(f"Error deleting original file {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Organize music files by metadata.")
    parser.add_argument("--input_path", type=str, required=True, help="Path to the folder containing music files.")
    parser.add_argument("--api_key", type=str, required=True, help="Your AcoustID API key.")
    parser.add_argument("--output_path", type=str, required=True, help="Path to output folder where organized files will be stored.")
    parser.add_argument("--contact_email", type=str, required=True, help="Contact email to use for the MusicBrainz API.")
    parser.add_argument(
        "--order_by",
        type=str,
        choices=[e.value for e in OrderBy],
        default=OrderBy.ARTIST.value,
        help="Criteria for organizing files: 'artist', 'album' or 'year'. Default is 'artist'."
    )
    parser.add_argument(
        "--remove_origin",
        action="store_true",
        default=False,
        help="If set, the original files will be deleted after copying. Default is False."
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=100,
        help="Number of files to process in each batch. Default is 100."
    )
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    api_key = args.api_key
    contact_email = args.contact_email
    order_by = args.order_by
    remove_origin = args.remove_origin
    batch_size = args.batch_size

    files = list(input_path.glob("**/*"))
    process_files_in_batches(files, batch_size, output_path, order_by, api_key, contact_email, remove_origin)

if __name__ == "__main__":
    main()