<?php

namespace App\Enums;

use BenSampo\Enum\Enum;

final class SubscriptionType extends Enum
{
    const BASIC     = 00;
    const MEMBER    = 10;
    const COMMITTEE = 20;
    const ADMIN     = 30;

    public static function getDescription($value): string
    {
        if ($value === self::BASIC) {
            return 'subscriber';
        } elseif ($value === self::MEMBER) {
            return 'member';
        } elseif ($value === self::COMMITTEE) {
            return 'committee member';
        } elseif ($value === self::ADMIN) {
            return 'administrator';
        }

        return parent::getDescription($value);
    }
}
