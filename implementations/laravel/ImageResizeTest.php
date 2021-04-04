<?php


namespace Tests\Feature;


use App\Utilities\ImageResize;
use Tests\TestCase;

class ImageResizeTest extends TestCase
{

    public function testUrl()
    {
        $imageUrl = 'https://example.com/image.jpg';

        $ir = new ImageResize($imageUrl);
        $actual = $ir->setDimensions(120, 200)->getUrl();

        $domain = rtrim(env('IMAGE_RESIZE_DOMAIN'), '/');
        $expected = $domain . '/s/120x200/' . base64_encode($imageUrl) . '/image.jpg';

        $this->assertEquals($expected, $actual);

    }

    public function testCorrectImage()
    {
        $imageUrl = 'https://example.com/image.jpg';

        $ir = new ImageResize($imageUrl);
        $actual = $ir->setDimensions(50, 75)->render();

        $domain = rtrim(env('IMAGE_RESIZE_DOMAIN'), '/');
        $url1 = $domain . '/s/50x75/' . base64_encode($imageUrl) . '/image.jpg';
        $url2 = $domain . '/s/100x150/' . base64_encode($imageUrl) . '/image.jpg';

        $expected = sprintf('<img src="%s" srcset="%s 1x, %s 2x"/>', $imageUrl, $url1, $url2);

        $this->assertEquals($expected, $actual);
    }

    public function testCorrectSignedImage()
    {
        $imageUrl = 'https://example.com/image.jpg';

        $ir = new ImageResize($imageUrl);
        $actual = $ir->setDimensions(50, 75)->sign(true)->render();

        $domain = rtrim(env('IMAGE_RESIZE_DOMAIN'), '/');
        $sgn = env('IMAGE_RESIZE_SIGNATURE');
        $url1 = $domain . '/s/50x75/' . base64_encode($imageUrl) . '/image.jpg?sgn=' . md5($imageUrl . $sgn);
        $url2 = $domain . '/s/100x150/' . base64_encode($imageUrl) . '/image.jpg?sgn=' . md5($imageUrl . $sgn);

        $expected = sprintf('<img src="%s" srcset="%s 1x, %s 2x"/>', $imageUrl, $url1, $url2);

        $this->assertEquals($expected, $actual);
    }

    public function testEscaping()
    {
        $imageUrl = 'https://example.com/image.jpg';

        $ir = new ImageResize($imageUrl);
        $actual = $ir->setDimensions(50, 75)->render([
            'title' => 'He said "it is mé"'
        ]);

        $domain = rtrim(env('IMAGE_RESIZE_DOMAIN'), '/');
        $url1 = $domain . '/s/50x75/' . base64_encode($imageUrl) . '/image.jpg';
        $url2 = $domain . '/s/100x150/' . base64_encode($imageUrl) . '/image.jpg';

        $expected = sprintf('<img title="He said &quot;it is mé&quot;" src="%s" srcset="%s 1x, %s 2x"/>', $imageUrl, $url1, $url2);

        $this->assertEquals($expected, $actual);
    }

    public function testNoWidthHeight()
    {
        $imageUrl = 'https://example.com/image.jpg';

        $this->expectException(\Exception::class);

        $ir = new ImageResize($imageUrl);
        $ir->getUrl();
    }

}
