<?php

namespace App\Utilities;

class ImageResize
{

    /**
     * The URL of the resize utility
     * @var string
     */
    private $resizeUrl;

    /**
     * The URL of the image to resize
     * @var string
     */
    private $imageUrl;

    /**
     * The width of the image
     * @var int
     */
    private $width;

    /**
     * The height if the image
     * @var int
     */
    private $height;

    /**
     * Image options (NYI)
     * @var array
     */
    private $options = [];

    /**
     * @var bool
     */
    private $sign = false;

    /**
     * The signature used to sign unknown images
     * @var bool
     */
    private $signature = false;

    /**
     * ImageResize constructor.
     * @param string $imageUrl The absolute URL of the image to resize
     */
    public function __construct(string $imageUrl)
    {
        $this->resizeUrl = env('IMAGE_RESIZE_DOMAIN');
        $this->signature = env('IMAGE_RESIZE_SIGNATURE');
        $this->imageUrl = trim($imageUrl);
    }

    /**
     * Set the dimensions of the output image
     * @param int $width
     * @param int $height
     * @return $this
     */
    public function setDimensions(int $width, int $height)
    {
        $this->width = $width;
        $this->height = $height;
        return $this;
    }

    /**
     * Override the default crop centering so that cropping happens on a different part of the image.
     * @param float $x A value between 0 and 1. Without this being set, the value is 0.5
     * @param float $y A value between 0 and 1. Without this being set, the value is 0.5
     * @return $this
     * @throws \Exception
     */
    public function centering(float $x, float $y)
    {
        if ($x < 0 || $y < 0 || $x > 1 || $y > 1) {
            throw new \Exception('Only values between 0 and 1 are allowed');
        }

        $this->options['c'] = [$x, $y];
        return $this;
    }

    /**
     * @param bool $status
     * @return $this
     */
    public function sign(bool $status)
    {
        $this->sign = $status;
        return $this;
    }

    /**
     * Get the generated URL for this image
     * @return string
     * @throws \Exception
     */
    public function getUrl()
    {
        if (!$this->width && !$this->height) {
            throw new \Exception('No width and height set');
        }

        $parts = [
            trim(rtrim($this->resizeUrl, '/')),
            's',
            "{$this->width}x{$this->height}",
            $this->getEncodedImageOptions(),
            urlencode(basename($this->imageUrl))
        ];

        $url = implode('/', $parts);

        if ($this->sign) {
            $url .= "?sgn=" . md5($this->imageUrl . $this->signature);
        }

        return $url;
    }

    /**
     * Render an image tag with src and srcset attributes
     * @param array $attributes Any other attributes to apply to the image
     * @return string
     * @throws \Exception
     */
    public function render(array $attributes = [])
    {
        $originalWidth = $this->width;
        $originalHeight = $this->height;

        $src = $this->imageUrl;
        $oneX = $this->getUrl();

        $this->width *= 2;
        $this->height *= 2;

        $twoX = $this->getUrl();

        $this->width = $originalWidth;
        $this->height = $originalHeight;

        $attributes['src'] = $src;
        $attributes['srcset'] = "{$oneX} 1x, {$twoX} 2x";

        $asString = [];

        foreach ($attributes as $key => $value) {
            $v = in_array($key, ['src', 'srcset']) ? $value : htmlspecialchars($value, ENT_QUOTES);
            $asString[] = sprintf('%s="%s"', $key, $v);
        }

        return '<img ' . implode(' ', $asString) . '/>';
    }

    /**
     * Get the encoded image options, which is either an encoded URL or an encoded JSON object of options
     * @return string
     */
    private function getEncodedImageOptions()
    {
        $toEncode = $this->imageUrl;

        if ($this->options) {
            $this->options['s'] = $this->imageUrl;
            $toEncode = json_encode($this->options);
        }

        return base64_encode($toEncode);
    }

}
