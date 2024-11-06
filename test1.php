<?php
// Define the file path to store the YouTube links
$videoFile = 'videos.txt';

// Check if the video file exists, if not create it
if (!file_exists($videoFile)) {
    file_put_contents($videoFile, ""); // Create an empty file if it doesn't exist
}

// Initialize an array to hold video links from the file
$videos = file($videoFile, FILE_IGNORE_NEW_LINES);

// Check if the form is submitted
if ($_SERVER["REQUEST_METHOD"] == "POST" && !empty($_POST['youtube_link'])) {
    $newVideo = $_POST['youtube_link'];

    // Validate the YouTube link (simple check to ensure it contains "youtube.com")
    if (filter_var($newVideo, FILTER_VALIDATE_URL) && strpos($newVideo, 'youtube.com') !== false) {
        // Append the new YouTube link to the video file
        file_put_contents($videoFile, $newVideo . PHP_EOL, FILE_APPEND);
        // Reload the page to reflect the new video
        header("Location: " . $_SERVER['PHP_SELF']);
        exit;
    } else {
        $error = "Please provide a valid YouTube link.";
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Portfolio</title>
    <link href="https://fonts.googleapis.com/css2?family=Lexend+Deca:wght@700&display=swap" rel="stylesheet">
    <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.5.2/dist/umd/popper.min.js"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
    <style>
        body { background-color: #000; color: #fff; }
        .navbar { background-color: transparent !important; }
        .navbar-nav .nav-link { color: #fff !important; }
        .content { padding-left: 250px; transition: padding-left 0.3s ease; }
        .title { font-size: 2.5rem; font-weight: bold; text-align: left; margin-bottom: 40px; }
    </style>
</head>
<body>
    <div class="container my-5 content">
        <h2 class="title">EDITED WORKS</h2>

        <!-- Display any error messages -->
        <?php if (isset($error)) { echo "<div class='alert alert-danger'>$error</div>"; } ?>

        <!-- Form to Add YouTube Video -->
        <form action="" method="POST">
            <div class="form-group">
                <label for="youtube_link">Add YouTube Link:</label>
                <input type="url" class="form-control" id="youtube_link" name="youtube_link" required placeholder="Paste YouTube Video Link">
            </div>
            <button type="submit" class="btn btn-primary">Add Video</button>
        </form>

        <div class="row mt-4">
            <?php foreach ($videos as $index => $video): ?>
                <div class="col-md-4 mb-4 thumbnail" data-toggle="modal" data-target="#videoModal" data-video="<?= $video ?>">
                    <div class="card">
                        <img src="https://img.youtube.com/vi/<?= basename($video) ?>/hqdefault.jpg" class="card-img" alt="Video <?= $index + 1 ?>">
                        <div class="card-body">
                            <h6 class="card-subtitle">WEDDING HIGHLIGHTS</h6>
                            <h5 class="card-title">Video <?= $index + 1 ?></h5>
                        </div>
                    </div>
                </div>
            <?php endforeach; ?>
        </div>
    </div>

    <!-- Video Modal -->
    <div class="modal fade" id="videoModal" tabindex="-1" role="dialog" aria-labelledby="videoModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered" role="document">
            <div class="modal-content">
                <div class="modal-body">
                    <iframe id="videoPlayer" src="" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Handle video modal click
        $('#videoModal').on('show.bs.modal', function (event) {
            var button = $(event.relatedTarget); // Button that triggered the modal
            var videoSrc = button.data('video'); // Extract info from data-* attributes
            var modal = $(this);
            modal.find('#videoPlayer').attr('src', videoSrc);
        });

        // Stop video when modal is closed
        $('#videoModal').on('hidden.bs.modal', function () {
            var modal = $(this);
            modal.find('#videoPlayer').attr('src', '');
        });
    </script>
</body>
</html>
