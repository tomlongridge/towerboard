<?php

namespace App\Enums;

use BenSampo\Enum\Enum;

final class UserContactVisibility extends Enum
{
    const NONE     = 00;
    const MEMBERS  = 10;
    const USERS    = 20;
    const EVERYONE = 30;

    public static function getDescription($value): string
    {
        if ($value === self::NONE) {
            return 'Private';
        } elseif ($value === self::MEMBERS) {
            return 'Members of the board';
        } elseif ($value === self::GUILD) {
            return 'Registered users of Towerboard';
        } elseif ($value === self::EVERYONE) {
            return 'Publicly visible to everyone';
        }

        return parent::getDescription($value);
    }
}
