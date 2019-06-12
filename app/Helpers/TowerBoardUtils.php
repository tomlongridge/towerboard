<?php

namespace App\Helpers;

class TowerBoardUtils
{
    public static function obscureEmail($email)
    {
        $emailSplit = explode("@", $email);

        $prefix = '';
        if (strlen($emailSplit[0]) > 6) {
            $prefix = substr($emailSplit[0], 0, 4);
        } else {
            $prefix = substr($emailSplit[0], 0, 1);
        }

        return $prefix . "...@..." . substr($emailSplit[1], 4);
    }

    public static function strToNoun($word)
    {
        return 'a' . (starts_with(strtolower($word), ['a', 'e', 'i', 'o', 'u']) ? 'n' : '') . " ${word}";
    }
}