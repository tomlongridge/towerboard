<?php

namespace App\Enums;

use BenSampo\Enum\Enum;

final class BoardType extends Enum
{
    const TOWER  = 10;
    const BRANCH = 20;
    const GUILD  = 30;

    public static function getDescription($value): string
    {
        if ($value === self::TOWER) {
            return 'Tower';
        } elseif ($value === self::BRANCH) {
            return 'Branch';
        } elseif ($value === self::GUILD) {
            return 'Guild';
        }

        return parent::getDescription($value);
    }
}
