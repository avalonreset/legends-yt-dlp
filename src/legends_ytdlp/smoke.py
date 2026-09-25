from __future__ import annotations

from dataclasses import dataclass

from .batch import BatchPaths, create_batch_from_urls


SMOKE_RIGHTS_BASIS = (
    "Official NASA Goddard public-facing videos for install validation; NASA media is generally not "
    "copyrighted unless noted, but operators must verify third-party restrictions before reuse."
)
CUSTOM_SMOKE_RIGHTS_BASIS = (
    "Operator-provided smoke-test URL for install validation; operator must verify permission, "
    "license, and platform terms before real download."
)


@dataclass(frozen=True)
class SmokeVideo:
    url: str
    title: str
    duration_seconds: int


SMOKE_VIDEOS: tuple[SmokeVideo, ...] = (
    SmokeVideo("https://www.youtube.com/watch?v=LeUcjqqhNxM", "NASA | The Big Bang", 15),
    SmokeVideo("https://www.youtube.com/watch?v=08rMlpvUP3w", "NASA | See Goddard in 3D!", 55),
    SmokeVideo(
        "https://www.youtube.com/watch?v=x_Akn8fUBeQ",
        "Doomed Neutron Stars Create Blast of Light and Gravitational Waves",
        43,
    ),
    SmokeVideo(
        "https://www.youtube.com/watch?v=crXGmeWFb9o",
        "360 Video: NASA Simulation Plunges Into a Black Hole",
        70,
    ),
    SmokeVideo(
        "https://www.youtube.com/watch?v=XW6_n2N4Fag",
        "Science Comes Alive at NASA Goddard - (short cut)",
        123,
    ),
)


def smoke_urls(count: int) -> list[str]:
    if count <= 0:
        raise ValueError("--count must be greater than 0")
    if count > len(SMOKE_VIDEOS):
        raise ValueError(f"--count cannot exceed {len(SMOKE_VIDEOS)}")
    return [video.url for video in SMOKE_VIDEOS[:count]]


def create_smoke_batch(
    *,
    count: int = 5,
    name: str = "nasa-goddard-smoke-pack",
    output_dir: str | None = None,
    max_height: int | None = 360,
    max_filesize: str | None = "75M",
) -> BatchPaths:
    return create_batch_from_urls(
        urls=smoke_urls(count),
        rights_basis=SMOKE_RIGHTS_BASIS,
        name=name,
        output_dir=output_dir,
        max_height=max_height,
        max_filesize=max_filesize,
    )


def create_custom_smoke_batch(
    *,
    urls: list[str],
    rights_basis: str = CUSTOM_SMOKE_RIGHTS_BASIS,
    name: str = "custom-smoke-pack",
    output_dir: str | None = None,
    max_height: int | None = 360,
    max_filesize: str | None = "75M",
) -> BatchPaths:
    if not urls:
        raise ValueError("At least one --url is required for a custom smoke batch")
    return create_batch_from_urls(
        urls=urls,
        rights_basis=rights_basis,
        name=name,
        output_dir=output_dir,
        max_height=max_height,
        max_filesize=max_filesize,
    )
