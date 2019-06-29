<?php

namespace App\Enums;

use BenSampo\Enum\Enum;

final class CommitteeRole extends Enum
{
    const NONE           = 00;
    const CHAIR          = 10;
    const RINGING_MASTER = 20;
    const TREASURER      = 30;
    const CORRESPONDENT  = 40;
    const SOCIAL         = 50;

    public static function getDescription($value): string
    {
        if ($value === self::NONE) {
            return 'none';
        } elseif ($value === self::CHAIR) {
            return 'chair';
        } elseif ($value === self::RINGING_MASTER) {
            return 'ringing master';
        } elseif ($value === self::TREASURER) {
            return 'treasurer';
        } elseif ($value === self::CORRESPONDENT) {
            return 'correspondent';
        } elseif ($value === self::SOCIAL) {
            return 'social secretary';
        }

        return parent::getDescription($value);
    }
}
