<?php

function imageResize(string $url):\App\Utilities\ImageResize
{
    return new \App\Utilities\ImageResize($url);
}
