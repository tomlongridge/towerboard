<?php

namespace App\Helpers;

use Carbon\Carbon;
use Carbon\CarbonInterface;

class Utils
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

    public static function dateToStr($date)
    {
        if ($date == null) {
            return '';
        }

        $now = Carbon::now();

        if ($date->year == $now->year) {
            return $date->format('l j F');
        } else {
            return $date->format('l j F Y');
        }
    }

    /**
     * Converts a PHP date into an HTML string for display.
     * If it's in the last week, a human difference string is shown.
     * Otherwise the date is shown (with the year if not current)
     */
    public static function dateToUserStr($date)
    {
        if ($date == null) {
            return '';
        }

        $now = Carbon::now();
        $fromNow = $date->diffInDays($now);

        if (($fromNow > -7) && ($fromNow < 7)) {
            return "<span data-toggle=\"tooltip\" title=\"" .
                   $date->format('l j F Y') .
                   "\">" .
                   $date->diffForHumans($now, ['syntax' => CarbonInterface::DIFF_RELATIVE_TO_NOW,
                                               'options' => Carbon::ONE_DAY_WORDS | Carbon::JUST_NOW]) .
                   "</span>";
        } elseif ($date->year == $now->year) {
            return $date->format('l j F');
        } else {
            return $date->format('l j F Y');
        }
    }
}
